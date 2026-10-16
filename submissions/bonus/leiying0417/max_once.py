"""Keyless, single MAX acquisition research. There is deliberately no live mode."""
import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
import rlp
from eth_abi import decode
from web3 import Web3
from dex_arbitrage import RPC, ADDR, WALLET, RPCS, data, selector, identity, normalized_router, SWAP, APPROVE
from observe import human, oriented

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'reports/max-once-dryrun'
# Never create or modify this future execution journal from a dry run.
INTENT = ROOT / 'reports/max-once-execution-intent.json'
FACTORIES = dict(A='0x34aefafb9b530b8bce29da9a67a2bafc6ed95b20', B='0x779e4c7c8945b35fc33fded1785c22709072d496')
GPO = '0x420000000000000000000000000000000000000F'
L1BLOCK = '0x4200000000000000000000000000000000000015'
ORACLE = {GPO.lower(): ('getL1Fee(bytes)', 'getL1FeeUpperBound(uint256)'), L1BLOCK.lower(): ('operatorFeeScalar()', 'operatorFeeConstant()')}
HASHES = dict(tUSDC='0xd27451ac71c1c72c72324e2dbe612d5e0648368561f3340e81d7086edea40f0a', MAX='0x90ff1d9c356ac9ba45592781a9fd7a233410870ab74f1b47aa43b79682a187e1', PoolA='0x711fa716407c476dc3044f72ac5026d103f7a7881911b271342d0a223bbc1cd8', PoolB='0x711fa716407c476dc3044f72ac5026d103f7a7881911b271342d0a223bbc1cd8')

def require(ok, reason):
    if not ok: raise ValueError(reason)

def units(text, cap=10**18):
    require(isinstance(text, str) and re.fullmatch(r'[0-9]+(?:[.][0-9]{1,18})?', text) is not None, 'INVALID_DECIMAL_PRECISION_OR_SIGN')
    a, _, b = text.partition('.')
    n = int(a)*10**18 + int(b.ljust(18, '0'))
    require(0 < n <= cap, 'AMOUNT_OUT_OF_RANGE')
    return n

def minimum(quote, bps):
    require(type(bps) is int and 0 <= bps <= 50, 'SLIPPAGE_OUT_OF_RANGE_0_TO_50_BPS')
    n = quote*(10000-bps)//10000
    require(n > 0, 'ZERO_MIN_OUT')
    return n

def once_gate(intent_exists=False, max_balance=0):
    require(not intent_exists, 'EXECUTION_INTENT_EXISTS_READ_TXHASH_FIRST_NO_RETRY')
    require(max_balance == 0, 'FIRST_ACQUISITION_ONLY_EXISTING_MAX')

def recovery(event):
    return dict(state='COMPLETE_STOP' if event == 'SWAP_SUCCESS' else 'FROZEN', max_swaps=1, new_swaps=False, auto_sell=False, auto_retry=False, next='READ_TXHASH_AND_RECEIPT_BEFORE_ANY_SEPARATE_REVIEW')

def make_plan(side, amount, out, allowance):
    require(side in ('A', 'B'), 'ROUTE_MISMATCH')
    require(type(amount) is int and 0 < amount <= 10**18 and out > 0, 'PLAN_LIMIT_OR_MINOUT')
    require(0 <= allowance <= amount, 'ALLOWANCE_EXCEEDS_PRINCIPAL_NO_IMPLICIT_REVOKE')
    def tx(to, sig, args): return dict(to=to, **{'from': WALLET}, data=data(sig,args), gas=hex(500000), value='0x0')
    calls=[]
    if allowance < amount: calls.append(tx(ADDR['tUSDC'],APPROVE,[ADDR['Router'+side],amount]))
    calls.append(tx(ADDR['Router'+side],SWAP,[amount,out,ADDR['tUSDC'],ADDR['MAX'],WALLET]))
    return calls

class SafeRPC(RPC):
    allowed = RPC.allowed | {'eth_maxPriorityFeePerGas'}
    def __init__(self, url=RPCS[0]):
        super().__init__(url)
        self.targets.update(FACTORIES.values()); self.expected_simulation=None
    def guard(self, method, params):
        if method == 'eth_simulateV1':
            require(self.expected_simulation is not None and params == self.expected_simulation, 'SIMULATION_NOT_EXACT_SINGLE_SWAP_PLAN')
            payload=params[0]
            require(set(payload)=={'blockStateCalls','validation','traceTransfers'} and payload['validation'] is False and len(payload['blockStateCalls'])==1, 'SIMULATION_OVERRIDE_FORBIDDEN')
            block=payload['blockStateCalls'][0]
            require(set(block)=={'calls'}, 'SIMULATION_OVERRIDE_FORBIDDEN')
            swaps=[]; approvals=[]
            for c in block['calls']:
                require(c.get('value','0x0')=='0x0', 'NONZERO_VALUE')
                clean={k:v for k,v in c.items() if k!='value'}
                RPC.guard(self,'eth_simulateV1',[{'blockStateCalls':[{'calls':[clean]}],'validation':False},params[1]])
                if c['data'][:10]==selector(SWAP):
                    a=decode(['uint256','uint256','address','address','address'],bytes.fromhex(c['data'][10:]))
                    require(c['to'] in (ADDR['RouterA'],ADDR['RouterB']) and 0<a[0]<=10**18 and a[1]>0 and a[2:]==(ADDR['tUSDC'].lower(),ADDR['MAX'].lower(),WALLET.lower()), 'SWAP_SCOPE_MISMATCH')
                    swaps.append((c,a))
                elif c['data'][:10]==selector(APPROVE):
                    a=decode(['address','uint256'],bytes.fromhex(c['data'][10:]))
                    require(c['to']==ADDR['tUSDC'], 'APPROVAL_TOKEN_MISMATCH')
                    approvals.append(a)
            require(len(swaps)==1 and len(approvals)<=1, 'MAX_SWAPS_ONE')
            if approvals: require(approvals[0]==(swaps[0][0]['to'].lower(),swaps[0][1][0]), 'APPROVAL_SCOPE_MISMATCH')
            return
        if method == 'eth_call' and params[0].get('to','').lower() in ORACLE:
            c=params[0]
            require(set(c)=={'to','data'} and c['data'][:10] in {selector(s) for s in ORACLE[c['to'].lower()]}, 'ORACLE_CALL_FORBIDDEN')
            return
        super().guard(method,params)

def fresh(header, end, now):
    require(header['hash']==end['hash'] and 0 <= now-int(header['timestamp'],16) <= 120, 'STALE_QUOTE_OR_REORG')

def budget_check(total, cap, eth):
    require(0 < cap <= 10**14 and 0 < total <= cap, 'GAS_BUDGET_EXCEEDED')
    require(eth >= cap, 'INSUFFICIENT_ETH_BUDGET')

def run(report, amount=10**18, bps=50, cap=10**14, rpc=None, *, _live_preflight=False):
    require(type(amount) is int and 0 < amount <= 10**18, 'AMOUNT_OUT_OF_RANGE')
    minimum(10**18,bps); budget_check(1,cap,cap); once_gate(False if _live_preflight else INTENT.exists())
    rpc=rpc or SafeRPC()
    identity(int(rpc.request('eth_chainId',[]),16),WALLET,ADDR)
    block=hex(int(rpc.request('eth_blockNumber',[]),16)-(0 if _live_preflight else 3))
    header=rpc.request('eth_getBlockByNumber',[block,False]); fresh(header,header,time.time())
    report.update(chain_id=84532,wallet=WALLET,rpc=rpc.url,block=dict(number=int(block,16),hash=header['hash'],timestamp=int(header['timestamp'],16),utc=datetime.fromtimestamp(int(header['timestamp'],16),timezone.utc).isoformat()),slippage_bps=bps,gas_budget_wei=str(cap),gas_budget_ETH=human(cap,18))
    def call(addr,sig,args=(),outs=('uint256',)): return rpc.call(addr,sig,args,outs,block)[0]
    codes={n:rpc.request('eth_getCode',[a,block]) for n,a in ADDR.items()}
    report['runtime_hashes']={n:Web3.to_hex(Web3.keccak(hexstr=c)) for n,c in codes.items()}
    for n,h in HASHES.items(): require(report['runtime_hashes'][n]==h,'PINNED_CODE_MISMATCH_'+n)
    source=json.loads((ROOT/'reports/dex-arbitrage/RouterA-verified.json').read_text())
    require(source.get('is_fully_verified') and source['deployed_bytecode'].lower()==codes['RouterA'].lower(),'VERIFIED_ROUTER_CODE_MISMATCH')
    for n in ('tUSDC','MAX'): require(call(ADDR[n],'decimals()')==18,'DECIMALS_MISMATCH')
    balances={n:call(ADDR[n],'balanceOf(address)',[WALLET]) for n in ('tUSDC','MAX')}
    balances['ETH']=int(rpc.request('eth_getBalance',[WALLET,block]),16)
    report['balances']={n:dict(raw=str(v),human=human(v,18)) for n,v in balances.items()}
    once_gate(False if _live_preflight else INTENT.exists(),balances['MAX']); require(balances['tUSDC']>=amount,'INSUFFICIENT_TUSDC')
    report['routes']={}; quotes={}
    for side in ('A','B'):
        router=ADDR['Router'+side]; pair=ADDR['Pool'+side]
        factory=call(router,'factory()',outs=('address',))
        require(factory.lower()==FACTORIES[side],'FACTORY_IDENTITY_MISMATCH')
        require(rpc.request('eth_getCode',[factory,block]) not in ('0x','0x0'),'FACTORY_NO_CODE')
        forward=call(factory,'getPair(address,address)',[ADDR['tUSDC'],ADDR['MAX']],('address',))
        reverse=call(factory,'getPair(address,address)',[ADDR['MAX'],ADDR['tUSDC']],('address',))
        require(forward.lower()==reverse.lower()==pair.lower(),'PAIR_ROUTE_MISMATCH')
        require(normalized_router(codes['Router'+side],factory)==normalized_router(codes['RouterA'],FACTORIES['A']),'ROUTER_IMPLEMENTATION_MISMATCH')
        t0=call(pair,'token0()',outs=('address',)); t1=call(pair,'token1()',outs=('address',))
        reserves=rpc.call(pair,'getReserves()',[],('uint112','uint112'),block)
        rin,rout=oriented(t0,t1,reserves,ADDR['tUSDC'],ADDR['MAX']); require(min(rin,rout)>0,'EMPTY_POOL')
        quotes[side]=call(router,'getAmountOut(uint256,uint256,uint256)',[amount,rin,rout])
        report['routes'][side]=dict(router=router,factory=factory,pair=pair,reverse_pair=reverse,quote_raw=str(quotes[side]),quote_MAX=human(quotes[side],18),verified=True)
    side=max(('A','B'),key=lambda s:quotes[s]); quote=quotes[side]; out=minimum(quote,bps)
    allowances={s:call(ADDR['tUSDC'],'allowance(address,address)',[WALLET,ADDR['Router'+s]]) for s in ('A','B')}
    report['candidate']=dict(side=side,amount_raw=str(amount),amount_tUSDC=human(amount,18),quote_raw=str(quote),quote_MAX=human(quote,18),minOut_raw=str(out),minOut_MAX=human(out,18),spender=ADDR['Router'+side],allowance_raw=str(allowances[side]),all_router_allowances_raw={s:str(a) for s,a in allowances.items()},recipient=WALLET,value=0)
    require(all(a<=amount for a in allowances.values()),'ALLOWANCE_EXCEEDS_PRINCIPAL_NO_IMPLICIT_REVOKE')
    plan=make_plan(side,amount,out,allowances[side]); report['plan']=plan
    report['planned_transaction_count']=len(plan)
    def balance(n): return dict(to=ADDR[n],data=data('balanceOf(address)',[WALLET]),gas=hex(100000),**{'from':WALLET})
    allowance_call=dict(to=ADDR['tUSDC'],data=data('allowance(address,address)',[WALLET,ADDR['Router'+side]]),gas=hex(100000),**{'from':WALLET})
    calls=[balance('tUSDC'),balance('MAX')]+plan+[balance('tUSDC'),balance('MAX'),allowance_call]
    payload=[dict(blockStateCalls=[dict(calls=calls)],validation=False,traceTransfers=True),block]
    rpc.expected_simulation=payload
    report['simulation_request']=payload
    sim=rpc.request('eth_simulateV1',payload); report['simulation_result']=sim
    rows=sim[0]['calls']; require(len(rows)==len(calls) and all(int(r['status'],16)==1 for r in rows),'SIMULATION_FAILED')
    val=lambda i:int(rows[i]['returnData'],16)
    require(val(0)==balances['tUSDC'] and val(1)==balances['MAX'] and val(-3)==balances['tUSDC']-amount and val(-2)-balances['MAX']==quote and val(-2)-balances['MAX']>=out and val(-1)==0,'SIMULATION_BALANCE_ALLOWANCE_ASSERTION_FAILED')
    gas=[int(rows[i+2]['gasUsed'],16) for i in range(len(plan))]
    report['simulation_summary']=dict(success=True,gas_used=gas,total_gas_used=sum(gas),final_tUSDC_raw=str(val(-3)),final_MAX_raw=str(val(-2)),final_allowance_raw=str(val(-1)),validation=False,notice='Shared simulated state only; no signatures, broadcasts, real approval, mempool validation or state overrides.')
    # Reviewed public fee logic from mint_once.py, never imported or executed it.
    for oracle in (GPO,L1BLOCK): require(rpc.request('eth_getCode',[oracle,block]) not in ('0x','0x0'),'FEE_ORACLE_NO_CODE')
    base=int(header['baseFeePerGas'],16); tip=int(rpc.request('eth_maxPriorityFeePerGas',[]),16)
    maxfee=3*base+tip; require(maxfee>0,'INVALID_FEE_CAP')
    scalar=call(L1BLOCK,'operatorFeeScalar()'); constant=call(L1BLOCK,'operatorFeeConstant()')
    nonce=int(rpc.request('eth_getTransactionCount',[WALLET,block]),16)
    require(nonce==int(rpc.request('eth_getTransactionCount',[WALLET,'pending']),16),'PENDING_NONCE_CHANGED')
    report['nonce']=nonce
    fees=[]
    for i,(tx,used) in enumerate(zip(plan,gas)):
        limit=(used*150+99)//100
        unsigned=b'\x02'+rlp.encode([84532,nonce+i,tip,maxfee,limit,bytes.fromhex(tx['to'][2:]),0,bytes.fromhex(tx['data'][2:]),[]])
        l1=call(GPO,'getL1Fee(bytes)',[unsigned])
        # Include pessimistic signature/framing overhead in size-based oracle bound.
        upper=call(GPO,'getL1FeeUpperBound(uint256)',[len(unsigned)+72])
        operator=constant+limit*scalar*100
        reserve=20*max(l1,upper)+20*operator+10**9
        fees.append(dict(gas_used=used,gas_limit=limit,maxFeePerGas_wei=maxfee,maxPriorityFeePerGas_wei=tip,l1_estimate_wei=l1,l1_size_upper_estimate_wei=upper,operator_scalar=scalar,operator_constant=constant,operator_conservative_wei=operator,extra_reserve_wei=reserve,total_budgeted_wei=limit*maxfee+reserve))
    total=sum(f['total_budgeted_wei'] for f in fees)
    report['fees']=dict(transactions=fees,total_budgeted_wei=str(total),total_budgeted_ETH=human(total,18),caveat='EIP1559 caps L2 execution only. L1/operator 20x reserve + 1e9 wei per transaction is a conservative estimate, NOT a protocol hard cap. Missing oracle estimate means WAIT. No ETH/tUSDC profit conversion required or profit claim.')
    budget_check(total,cap,balances['ETH'])
    fresh(header,rpc.request('eth_getBlockByNumber',[block,False]),time.time())
    once_gate(False if _live_preflight else INTENT.exists())
    report.update(status='DRY_RUN_READY',reason_codes=[],fresh_at_completion=True)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--amount',default='1'); p.add_argument('--slippage-bps',type=int,default=50)
    p.add_argument('--gas-budget-eth',default='0.0001'); p.add_argument('--rpc',choices=RPCS,default=RPCS[0])
    p.add_argument('--dry-run',action='store_true')
    args=p.parse_args(argv)  # --live / --execute are unrecognized and rejected.
    report=dict(status='WAIT',reason_codes=[],started_utc=datetime.now(timezone.utc).isoformat(),dry_run=True,execution_authorized=False,max_swaps=1,auto_sell=False,auto_retry=False,broadcast_count=0)
    try: run(report,units(args.amount),args.slippage_bps,units(args.gas_budget_eth,10**14),SafeRPC(args.rpc))
    except Exception as e: report.update(status='WAIT',reason_codes=[type(e).__name__+': '+str(e)])
    report['finished_utc']=datetime.now(timezone.utc).isoformat()
    OUT.mkdir(parents=True,exist_ok=True)
    body=json.dumps(report,indent=2,ensure_ascii=False)+'\n'
    (OUT/'latest.json').write_text(body)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    with (OUT/('decision-'+stamp+'.json')).open('x') as f: f.write(body)
    print(json.dumps({k:v for k,v in report.items() if k not in ('simulation_request','simulation_result','runtime_hashes','plan')},indent=2,ensure_ascii=False))
    return 0 if report['status']=='DRY_RUN_READY' else 2

if __name__=='__main__': raise SystemExit(main())
