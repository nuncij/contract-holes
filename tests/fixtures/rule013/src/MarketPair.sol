// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAggregatorV3 {
    function latestRoundData()
        external
        view
        returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        );
}

interface IAmmPair {
    function getReserves()
        external
        view
        returns (uint112 reserve0, uint112 reserve1, uint32 timestamp);
}

interface ITwapOracle {
    function consult() external view returns (uint256 price);
}

interface IRouter {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address recipient,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

contract MarketVulnerable {
    uint256 public lastPrice;

    function useStalePrice(IAggregatorV3 feed) external {
        (, int256 answer, , , ) = feed.latestRoundData();
        lastPrice = uint256(answer);
    }

    function useSpotPrice(IAmmPair pair) external {
        (uint112 reserve0, uint112 reserve1, ) = pair.getReserves();
        lastPrice = uint256(reserve1) * 1e18 / uint256(reserve0);
    }

    function unsafeSwap(
        IRouter router,
        uint256 amountIn,
        address[] calldata path
    ) external {
        router.swapExactTokensForTokens(
            amountIn,
            0,
            path,
            address(this),
            block.timestamp
        );
    }
}

contract MarketSafe {
    uint256 public lastPrice;

    function useFreshPrice(IAggregatorV3 feed, uint256 maxAge) external {
        (, int256 answer, , uint256 updatedAt, ) = feed.latestRoundData();
        require(updatedAt != 0, "incomplete round");
        require(block.timestamp - updatedAt <= maxAge, "stale price");
        lastPrice = uint256(answer);
    }

    function useTwap(ITwapOracle oracle) external {
        lastPrice = oracle.consult();
    }

    function safeSwap(
        IRouter router,
        uint256 amountIn,
        uint256 minimumOutput,
        uint256 deadline,
        address[] calldata path
    ) external {
        router.swapExactTokensForTokens(
            amountIn,
            minimumOutput,
            path,
            address(this),
            deadline
        );
    }
}
