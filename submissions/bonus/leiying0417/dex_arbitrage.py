"""GUANGYING research planner: RPC reads/simulation only; no signer or broadcast path."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal
import requests
from web3 import Web3
from eth_abi import encode, decode
from observe import oriented, to_units, human

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports/dex-arbitrage"
WALLET = "0x3AF10AC46be1148ABADEe3C7168e27F960e0153d"
ADDR = dict(tUSDC="0x6797beC4DC1D4444Fe81790c47e9FB91e491Ac69", MAX="0x22201343039BB6418546978b447a45ee49f8dAa5", RouterA="0x2fc7C313bf38f0af4D92E8bE7347500D39174b82", RouterB="0x19272Cae94B8e3BCd7d6752823F40b925C5dad3C", PoolA="0xEf12cfd16d5e7903b837b2EfECBcdb1A0b5349D8", PoolB="0x07a45F3560d1bbF708027D9CcD8Ac95FBcaaD73d")
RPCS = ("https://base-sepolia-rpc.publicnode.com", "https://sepolia.base.org")
READ_SIGS = ("factory()", "getPair(address,address)", "token0()", "token1()", "getReserves()", "decimals()", "balanceOf(address)", "allowance(address,address)", "getAmountOut(uint256,uint256,uint256)")
SWAP = "swapExactTokensForTokens(uint256,uint256,address,address,address)"
APPROVE = "approve(address,uint256)"
DEFAULTS = dict(research_only=True, slippage_bps_per_leg=50, min_net_tUSDC="0.1", single_limit_tUSDC="50", daily_limit_tUSDC="50", stop_loss_tUSDC="1", max_age_seconds=120, user_parameters_confirmed=False, final_authorization=False, non_atomic_risk_accepted=False)

def selector(sig):
    return '0x' + Web3.keccak(text=sig)[:4].hex()

def data(sig, args=()):
    types = sig.split('(')[1][:-1].split(',') if not sig.endswith('()') else []
    return selector(sig) + encode(types, args).hex()

class RPC:
    allowed = {'eth_chainId','eth_blockNumber','eth_getBlockByNumber','eth_getCode','eth_getBalance','eth_getTransactionCount','eth_gasPrice','eth_call','eth_simulateV1'}
    def __init__(self, url=RPCS[0]):
        if url not in RPCS: raise ValueError('RPC_ENDPOINT_MISMATCH')
        self.url=url; self.session=requests.Session(); self.session.trust_env=False
        self.targets={x.lower() for x in ADDR.values()} | {WALLET.lower()}
    def guard(self, method, params):
        if method not in self.allowed: raise PermissionError('RPC_WRITE_FORBIDDEN')
        calls=[]
        if method == 'eth_call': calls=[params[0]]
        if method == 'eth_simulateV1':
            payload=params[0]
            if set(payload)-{'blockStateCalls','validation','traceTransfers'}: raise PermissionError('SIM_OVERRIDE_FORBIDDEN')
            for block in payload['blockStateCalls']:
                if set(block)!={'calls'}: raise PermissionError('SIM_OVERRIDE_FORBIDDEN')
                calls.extend(block['calls'])
        for call in calls:
            if set(call)-{'to','from','data','gas'} or call['to'].lower() not in self.targets: raise PermissionError('CALL_TARGET_FORBIDDEN')
            if 'from' in call and call['from'].lower()!=WALLET.lower(): raise PermissionError('WALLET_MISMATCH')
            sigs=READ_SIGS + ((APPROVE,SWAP) if method=='eth_simulateV1' else ())
            if call['data'][:10] not in {selector(s) for s in sigs}: raise PermissionError('SELECTOR_FORBIDDEN')
    def request(self, method, params):
        self.guard(method,params)
        r=self.session.post(self.url,json={'jsonrpc':'2.0','id':1,'method':method,'params':params},headers={'User-Agent':'Mozilla/5.0 (GUANGYING keyless research)','Accept':'application/json'},timeout=30)
        r.raise_for_status(); result=r.json()
        if 'error' in result: raise RuntimeError(json.dumps(result['error']))
        return result['result']
    def call(self, address, sig, args, outputs, block):
        raw=self.request('eth_call',[{'to':address,'data':data(sig,args)},block])
        return decode(outputs,bytes.fromhex(raw[2:]))

def identity(chain,wallet,addresses):
    if chain!=84532: raise ValueError('CHAIN_MISMATCH')
    if wallet.lower()!=WALLET.lower(): raise ValueError('WALLET_MISMATCH')
    if addresses!=ADDR: raise ValueError('ADDRESS_MISMATCH')

def minout(n,bps=50):
    if n<=0 or not 0<=bps<10000: raise ValueError('INVALID_MIN_OUT')
    v=n*(10000-bps)//10000
    if v<=0: raise ValueError('ZERO_MIN_OUT')
    return v

def plan(first,second,amount,intermediate,minimum1,minimum2):
    if first==second or {first,second}!={'A','B'} or min(amount,intermediate,minimum1,minimum2)<=0 or intermediate!=minimum1: raise ValueError('INVALID_PLAN')
    def call(to,sig,args): return {'from':WALLET,'to':to,'data':data(sig,args),'gas':hex(500000)}
    # Sell only guaranteed first-leg minOut, not a larger optimistic quote; leftover MAX is excluded from profit.
    return [call(ADDR['tUSDC'],APPROVE,[ADDR['Router'+first],amount]),call(ADDR['Router'+first],SWAP,[amount,minimum1,ADDR['tUSDC'],ADDR['MAX'],WALLET]),call(ADDR['MAX'],APPROVE,[ADDR['Router'+second],intermediate]),call(ADDR['Router'+second],SWAP,[intermediate,minimum2,ADDR['MAX'],ADDR['tUSDC'],WALLET])]

def decision(gross_floor,simulation_ok,gas_tusdc=None,routes_ok=True,fresh=True,within_limits=True):
    reasons=[]
    if gross_floor<=0: reasons.append('NONPOSITIVE_SLIPPAGE_FLOOR')
    if gas_tusdc is None: reasons.append('GAS_CONVERSION_MISSING')
    elif Decimal(human(gross_floor,18))-Decimal(gas_tusdc)<Decimal(DEFAULTS['min_net_tUSDC']): reasons.append('MIN_NET_NOT_MET')
    if not simulation_ok: reasons.append('STATEFUL_SIMULATION_FAILED')
    if not routes_ok: reasons.append('ROUTE_UNVERIFIED')
    if not fresh: reasons.append('STALE_BLOCK')
    if not within_limits: reasons.append('CAPITAL_OR_DAILY_LIMIT')
    reasons += ['L1_OPERATOR_FEE_UNVERIFIED','USER_RISK_PARAMETERS_MISSING','DAILY_USAGE_UNKNOWN','STOP_LOSS_STATE_UNKNOWN','NONATOMIC_LIVE_DISABLED','FINAL_AUTHORIZATION_MISSING']
    return dict(action='WAIT',recommended_tUSDC='0',reason_codes=reasons,net_tUSDC=None)

def recovery(state,event,actual_max=None,tx_status=None):
    if state=='FROZEN': return dict(state='FROZEN',new_trades=False,next='READ_BALANCE_RECEIPTS_REQUOTE_RESIMULATE_SEPARATE_AUTHORIZATION',actual_MAX=actual_max,tx_status=tx_status)
    if event=='LEG1_SUCCESS': return dict(state='MAX_EXPOSURE',new_trades=False)
    if event in ('LEG2_FAILED','LEG2_UNKNOWN'): return recovery('FROZEN',event,actual_max,tx_status)
    if event=='LEG2_SUCCESS' and state=='MAX_EXPOSURE': return dict(state='COMPLETE',new_trades=False)
    return dict(state='IDLE',new_trades=False)

def normalized_router(code,factory):
    # Verified Router.factory is immutable, embedded as PUSH32 at each read site.
    return code.lower().replace('000000000000000000000000'+factory.lower()[2:],'0'*64)

def run(report):
    rpc=RPC(); chain=int(rpc.request('eth_chainId',[]),16); identity(chain,WALLET,ADDR)
    height=int(rpc.request('eth_blockNumber',[]),16)-3; block=hex(height)
    header=rpc.request('eth_getBlockByNumber',[block,False])
    report.update(chain_id=chain,wallet=WALLET,block=header,defaults=DEFAULTS,addresses=ADDR,rpc=rpc.url)
    def call(addr,sig,args=(),outs=('uint256',)): return rpc.call(addr,sig,args,outs,block)
    balances={n:call(ADDR[n],'balanceOf(address)',[WALLET])[0] for n in ('tUSDC','MAX')}
    balances['ETH']=int(rpc.request('eth_getBalance',[WALLET,block]),16)
    report['balances']={n:human(v,18) for n,v in balances.items()}
    report['nonce']=int(rpc.request('eth_getTransactionCount',[WALLET,block]),16)
    for n in ('tUSDC','MAX'):
        if call(ADDR[n],'decimals()')[0]!=18: raise ValueError('DECIMALS_MISMATCH')
    report['allowances']={n+'_'+r:str(call(ADDR[n],'allowance(address,address)',[WALLET,ADDR[r]])[0]) for n in ('tUSDC','MAX') for r in ('RouterA','RouterB')}
    source=json.loads((OUT/'RouterA-verified.json').read_text())
    codeA=rpc.request('eth_getCode',[ADDR['RouterA'],block]); report['routes']={}; pools={}
    if not source.get('is_fully_verified') or source.get('deployed_bytecode','').lower()!=codeA.lower(): raise ValueError('VERIFIED_RUNTIME_MISMATCH')
    factoryA=call(ADDR['RouterA'],'factory()',outs=('address',))[0]
    for dex in ('A','B'):
        router=ADDR['Router'+dex]; factory=call(router,'factory()',outs=('address',))[0]; rpc.targets.add(factory.lower())
        pair=call(factory,'getPair(address,address)',[ADDR['tUSDC'],ADDR['MAX']],('address',))[0]
        reverse=call(factory,'getPair(address,address)',[ADDR['MAX'],ADDR['tUSDC']],('address',))[0]
        code=rpc.request('eth_getCode',[router,block])
        ok=pair.lower()==ADDR['Pool'+dex].lower()==reverse.lower() and normalized_router(code,factory)==normalized_router(codeA,factoryA)
        report['routes'][dex]=dict(router=router,factory=factory,pair=pair,reverse_pair=reverse,verified=ok,runtime_keccak=Web3.to_hex(Web3.keccak(hexstr=code)),proof='RouterA full verified runtime exact match; RouterB runtime equal after factory immutable normalization')
        if not ok: raise ValueError('ROUTE_OR_RUNTIME_MISMATCH')
        t0=call(pair,'token0()',outs=('address',))[0]; t1=call(pair,'token1()',outs=('address',))[0]; rs=call(pair,'getReserves()',outs=('uint112','uint112'))
        pools[dex]=oriented(t0,t1,rs,ADDR['tUSDC'],ADDR['MAX'])
    report['pools']={d:dict(tUSDC=human(rs[0],18),MAX=human(rs[1],18),tUSDC_per_MAX=str(Decimal(rs[0])/Decimal(rs[1]))) for d,rs in pools.items()}
    def quote(d,n,reverse=False):
        rs=pools[d][::-1] if reverse else pools[d]
        return call(ADDR['Router'+d],'getAmountOut(uint256,uint256,uint256)',[n,*rs])[0]
    gasprice=int(rpc.request('eth_gasPrice',[]),16); report['gas_price_wei']=gasprice
    report['grid']=[]
    for n in (1,5,10,25,50):
        amount=n*10**18
        for first,second in (('A','B'),('B','A')):
            mx=quote(first,amount); m1=minout(mx); q2=quote(second,mx,True); conservative=quote(second,m1,True); m2=minout(conservative)
            report['grid'].append(dict(direction=first+'->'+second,amount_tUSDC=str(n),within_balance=amount<=balances['tUSDC'],quote_MAX=human(mx,18),second_input_MAX=human(m1,18),quote_return_tUSDC=human(q2,18),gross_tUSDC=human(q2-amount,18),slippage_floor_tUSDC=human(m2-amount,18),minOut1_raw=str(m1),minOut2_raw=str(m2)))
    candidates=[r for r in report['grid'] if r['within_balance'] and Decimal(r['amount_tUSDC'])<=Decimal(DEFAULTS['single_limit_tUSDC'])]
    if not candidates: raise ValueError('INSUFFICIENT_TUSDC')
    best=max(candidates,key=lambda r:Decimal(r['slippage_floor_tUSDC'])); report['research_candidate']=best
    first,second=best['direction'].split('->'); amount=to_units(best['amount_tUSDC'],18); m1=int(best['minOut1_raw']);m2=int(best['minOut2_raw'])
    calls=plan(first,second,amount,m1,m1,m2)
    report['finite_allowance_plan']=[dict(token=ADDR['tUSDC'],spender=ADDR['Router'+first],amount_raw=str(amount)),dict(token=ADDR['MAX'],spender=ADDR['Router'+second],amount_raw=str(m1))]
    report['plan_notice']='SIMULATION ONLY. Both exact approvals finite; first minOut equals second input; extra MAX retained and valued at zero. No deadline in verified ABI. Requote after first actual receipt; no automatic execution.'
    balance_call=lambda n: {'from':WALLET,'to':ADDR[n],'data':data('balanceOf(address)',[WALLET]),'gas':hex(100000)}
    # One sequential simulated block: approvals/swaps share EVM state; final balances prove state propagation.
    simcalls=[balance_call('tUSDC'),balance_call('MAX'),calls[0],calls[1],balance_call('MAX'),calls[2],calls[3],balance_call('tUSDC'),balance_call('MAX')]
    payload=[{'blockStateCalls':[{'calls':simcalls}],'validation':False,'traceTransfers':True},block]
    report['simulation_request']=payload
    simok=False
    try:
        result=rpc.request('eth_simulateV1',payload); report['simulation_result']=result
        results=result[0]['calls']; successful=len(results)==9 and all(int(c['status'],16)==1 for c in results)
        vals={i:int(results[i]['returnData'],16) for i in (0,1,4,7,8)} if successful else {}
        expected_mx=to_units(best['quote_MAX'],18)
        simok=successful and vals[0]==balances['tUSDC'] and vals[1]==balances['MAX'] and vals[4]-vals[1]==expected_mx and vals[8]-vals[1]==expected_mx-m1 and vals[7]-vals[0]>=m2-amount
        gas=sum(int(results[i]['gasUsed'],16) for i in (2,3,5,6))
        report['simulation_summary']=dict(success=simok,method='eth_simulateV1 shared sequential state; no state overrides, no signatures; validation=false is execution simulation NOT mempool/fee validation',balance_raw={str(k):str(v) for k,v in vals.items()},transaction_gas=gas,l2_execution_estimate_ETH=human(gas*gasprice,18),full_fee_estimate=None)
        if gas*gasprice:
            for row in report['grid']:
                row['break_even_tUSDC_per_ETH_l2_only_upper_bound']=str(Decimal(row['slippage_floor_tUSDC'])/Decimal(human(gas*gasprice,18))) if Decimal(row['slippage_floor_tUSDC'])>0 else None
                row['break_even_note']='No positive gas valuation can rescue a negative floor' if Decimal(row['slippage_floor_tUSDC'])<=0 else 'Illustrative using candidate gas only; excludes L1/operator fees, not a full net estimate'
    except Exception as exc: report['simulation_error']=str(exc)
    end=rpc.request('eth_getBlockByNumber',[block,False])
    fresh=0<=time.time()-int(header['timestamp'],16)<=DEFAULTS['max_age_seconds'] and end['hash']==header['hash']
    report['fresh_at_completion']=fresh
    report['decision']=decision(to_units(best['minOut2_raw'],0)-amount,simok,fresh=fresh)
    report['status']='complete_readonly'

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    report=dict(started_utc=datetime.now(timezone.utc).isoformat(),status='incomplete',decision=dict(action='WAIT',recommended_tUSDC='0'))
    try: run(report)
    except Exception as exc:
        report['error']=dict(type=type(exc).__name__,message=str(exc));report['decision']['reason_codes']=['READONLY_CHECK_FAILED',str(exc)]
    report['finished_utc']=datetime.now(timezone.utc).isoformat()
    text=json.dumps(report,ensure_ascii=False,indent=2)+chr(10)
    (OUT/'latest.json').write_text(text)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    (OUT/('decision-'+stamp+'.json')).write_text(text)
    print(json.dumps({k:report.get(k) for k in ('status','balances','pools','research_candidate','simulation_summary','decision','error')},ensure_ascii=False,indent=2))
    return 0 if report['status']=='complete_readonly' else 1

if __name__=='__main__': raise SystemExit(main())
