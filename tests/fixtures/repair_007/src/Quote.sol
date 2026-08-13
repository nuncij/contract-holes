// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IOracle {
    function quote() external view returns (address);
}

contract Quote {
    function entry(address a, address b) external view returns (address) {
        address expectedQuoteToken;
        expectedQuoteToken = verifyQuoteToken(expectedQuoteToken, a);
        expectedQuoteToken = verifyQuoteToken(expectedQuoteToken, b);
        return expectedQuoteToken;
    }

    function verifyQuoteToken(address _expected, address _oracle) internal view returns (address) {
        if (_oracle == address(0)) return _expected;
        return IOracle(_oracle).quote();
    }
}
