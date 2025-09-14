require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.17",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
      accounts: {
        mnemonic: "test test test test test test test test test test test junk"
      }
    },
    polygonZkEvmTestnet: {
      url: process.env.POLYGON_RPC_URL || "https://rpc.public.zkevm-test.net",
      chainId: 1442,
      accounts: process.env.ANCHORER_PRIVATE_KEY ? [process.env.ANCHORER_PRIVATE_KEY] : []
    },
    hardhat: {
      chainId: 31337
    }
  },
  etherscan: {
    apiKey: {
      polygonZkEvmTestnet: process.env.ETHERSCAN_API_KEY || ""
    },
    customChains: [
      {
        network: "polygonZkEvmTestnet",
        chainId: 1442,
        urls: {
          apiURL: "https://api-testnet-zkevm.polygonscan.com/api",
          browserURL: "https://testnet-zkevm.polygonscan.com"
        }
      }
    ]
  },
  gasReporter: {
    enabled: process.env.REPORT_GAS !== undefined,
    currency: "USD"
  }
};
