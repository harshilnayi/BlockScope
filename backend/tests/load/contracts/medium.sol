pragma solidity ^0.8.0;

contract Medium {
    uint256 public total;

    function add(uint256 x) public {
        total += x;
    }

    function sub(uint256 x) public {
        total -= x;
    }

    function mul(uint256 x) public {
        total *= x;
    }

    function div(uint256 x) public {
        require(x != 0);
        total /= x;
    }
}
