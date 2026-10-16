// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @title SimpleLend —— your own on-chain pawnshop (over-collateralized lending + liquidation)
/// @notice The flagship contract for Week 2, Lesson 4. Compare with lend.py (the Python intuition version) —— the same "health factor" math, here as an on-chain contract.
///         Teaching simplification: a single collateral + a single borrow asset, with the price fed manually by the admin (a simulated oracle),
///         so that in class you can "slash the ETH price on the spot" to trigger a liquidation.
contract SimpleLend {
    IERC20 public immutable collateral; // collateral, e.g. WETH
    IERC20 public immutable debtToken;  // the borrowed asset, e.g. USDC

    /// Collateral price: how much debtToken one unit of collateral is worth, scaled by 1e18 (e.g. 2000e18 = $2000)
    uint256 public price;
    address public admin;

    /// Liquidation threshold 80%: only 80% of collateral value can be used to support debt
    uint256 public constant LIQ_THRESHOLD_BPS = 8000;
    /// Liquidation bonus 110%: the liquidator repays 1 unit of debt and takes 1.1 units worth of collateral (a 10% discount incentive)
    uint256 public constant LIQ_BONUS_BPS = 11000;
    uint256 public constant WAD = 1e18;

    mapping(address => uint256) public collateralOf; // collateral each person deposited (1e18)
    mapping(address => uint256) public debtOf;        // each person's debt (1e18)

    event Deposit(address indexed who, uint256 amount);
    event Withdraw(address indexed who, uint256 amount);
    event Borrow(address indexed who, uint256 amount);
    event Repay(address indexed who, uint256 amount);
    event Liquidate(address indexed liquidator, address indexed user, uint256 repaid, uint256 seized);
    event PriceUpdated(uint256 newPrice);

    constructor(address _collateral, address _debtToken, uint256 _price) {
        collateral = IERC20(_collateral);
        debtToken = IERC20(_debtToken);
        price = _price;
        admin = msg.sender;
    }

    // ---- Oracle (for teaching: manual price feed, so liquidations can be created on the spot) ----

    /// Only the admin can change the price. In the real world this is an oracle like Chainlink; here it is simulated manually.
    function setPrice(uint256 newPrice) external {
        require(msg.sender == admin, "only admin");
        require(newPrice > 0, "zero price");
        price = newPrice;
        emit PriceUpdated(newPrice);
    }

    // ---- Deposit / Borrow / Repay / Withdraw ----

    /// Deposit collateral
    function deposit(uint256 amount) external {
        require(amount > 0, "zero");
        collateral.transferFrom(msg.sender, address(this), amount);
        collateralOf[msg.sender] += amount;
        emit Deposit(msg.sender, amount);
    }

    /// Borrow debtToken —— after borrowing the position must still be healthy (HF >= 1)
    function borrow(uint256 amount) external {
        require(amount > 0, "zero");
        debtOf[msg.sender] += amount;
        require(healthFactor(msg.sender) >= WAD, "would be unhealthy");
        debtToken.transfer(msg.sender, amount);
        emit Borrow(msg.sender, amount);
    }

    /// Repay debt
    function repay(uint256 amount) external {
        uint256 d = debtOf[msg.sender];
        if (amount > d) amount = d;
        debtToken.transferFrom(msg.sender, address(this), amount);
        debtOf[msg.sender] = d - amount;
        emit Repay(msg.sender, amount);
    }

    /// Withdraw collateral —— after withdrawing the position must still be healthy
    function withdraw(uint256 amount) external {
        require(collateralOf[msg.sender] >= amount, "too much");
        collateralOf[msg.sender] -= amount;
        require(healthFactor(msg.sender) >= WAD, "would be unhealthy");
        collateral.transfer(msg.sender, amount);
        emit Withdraw(msg.sender, amount);
    }

    // ---- Liquidation ----

    /// Liquidate a position with HF < 1: the liquidator repays all of its debt and takes the collateral at a 110% discounted rate.
    /// Teaching simplification: repay all debt at once (real Aave has a 50% close factor, liquidating in parts).
    function liquidate(address user) external {
        require(healthFactor(user) < WAD, "healthy, cannot liquidate");
        uint256 debt = debtOf[user];
        require(debt > 0, "no debt");

        // Amount of collateral the liquidator takes = debt value * 110% / price
        uint256 seize = (debt * LIQ_BONUS_BPS / 10000) * WAD / price;
        uint256 userCol = collateralOf[user];
        if (seize > userCol) seize = userCol; // if collateral is insufficient, take it all (bad debt, only in extreme markets)

        debtToken.transferFrom(msg.sender, address(this), debt); // the liquidator repays the debt
        debtOf[user] = 0;
        collateralOf[user] = userCol - seize;
        collateral.transfer(msg.sender, seize); // collateral goes to the liquidator

        emit Liquidate(msg.sender, user, debt, seize);
    }

    // ---- Read-only ----

    /// Collateral value (denominated in debtToken, 1e18)
    function collateralValue(address user) public view returns (uint256) {
        return collateralOf[user] * price / WAD;
    }

    /// Health factor (1e18 = 1.0). No debt → returns the max value (always safe).
    /// HF = collateral value * liquidation threshold / debt
    function healthFactor(address user) public view returns (uint256) {
        uint256 debt = debtOf[user];
        if (debt == 0) return type(uint256).max;
        uint256 adjusted = collateralValue(user) * LIQ_THRESHOLD_BPS / 10000;
        return adjusted * WAD / debt;
    }
}
