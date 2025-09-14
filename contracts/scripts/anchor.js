const { ethers } = require("hardhat");
const fs = require("fs");

async function main() {
  // Parse command line arguments
  const args = process.argv.slice(2);
  let rootHash = null;
  let contractAddress = null;
  
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--root" && i + 1 < args.length) {
      rootHash = args[i + 1];
    }
    if (args[i] === "--contract" && i + 1 < args.length) {
      contractAddress = args[i + 1];
    }
  }
  
  // Default root for testing
  if (!rootHash) {
    rootHash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef";
    console.log(`⚠️  No --root provided, using default: ${rootHash}`);
  }
  
  // Get contract address from deployment.json or command line
  if (!contractAddress) {
    try {
      const deploymentInfo = JSON.parse(fs.readFileSync("deployment.json", "utf8"));
      contractAddress = deploymentInfo.contractAddress;
      console.log(`📍 Using contract address from deployment.json: ${contractAddress}`);
    } catch (error) {
      console.error("❌ No contract address found. Deploy contract first or use --contract flag");
      process.exit(1);
    }
  }
  
  console.log("⚓ Anchoring Merkle root to blockchain...");
  console.log(`🌳 Root Hash: ${rootHash}`);
  console.log(`📍 Contract: ${contractAddress}`);
  console.log(`🌐 Network: ${hre.network.name}`);
  
  // Get contract instance
  const ComplianceAnchor = await ethers.getContractFactory("ComplianceAnchor");
  const complianceAnchor = ComplianceAnchor.attach(contractAddress);
  
  // Get signer
  const [signer] = await ethers.getSigners();
  console.log(`👤 Anchoring from: ${signer.address}`);
  
  try {
    // Call anchorRoot function
    const tx = await complianceAnchor.anchorRoot(rootHash);
    console.log(`📤 Transaction sent: ${tx.hash}`);
    
    // Wait for confirmation
    console.log("⏳ Waiting for confirmation...");
    const receipt = await tx.wait();
    
    console.log("✅ Root anchored successfully!");
    console.log(`🔗 Transaction Hash: ${receipt.hash}`);
    console.log(`📦 Block Number: ${receipt.blockNumber}`);
    console.log(`⛽ Gas Used: ${receipt.gasUsed.toString()}`);
    
    // Parse events
    const events = receipt.logs.map(log => {
      try {
        return complianceAnchor.interface.parseLog(log);
      } catch (error) {
        return null;
      }
    }).filter(event => event !== null);
    
    if (events.length > 0) {
      const rootAnchoredEvent = events.find(e => e.name === "RootAnchored");
      if (rootAnchoredEvent) {
        console.log("\n📋 Event Details:");
        console.log(`   Root: ${rootAnchoredEvent.args.root}`);
        console.log(`   Timestamp: ${rootAnchoredEvent.args.timestamp}`);
        console.log(`   Anchored By: ${rootAnchoredEvent.args.by}`);
      }
    }
    
    // Explorer link (if on testnet)
    if (hre.network.name === "polygonZkEvmTestnet") {
      console.log(`🔍 View on Explorer: https://testnet-zkevm.polygonscan.com/tx/${receipt.hash}`);
    }
    
    return {
      txHash: receipt.hash,
      blockNumber: receipt.blockNumber,
      gasUsed: receipt.gasUsed.toString(),
      root: rootHash,
      timestamp: Date.now()
    };
    
  } catch (error) {
    console.error("❌ Anchoring failed:", error.message);
    
    if (error.message.includes("Root cannot be zero")) {
      console.error("💡 Hint: Make sure root hash is not 0x0000...");
    }
    
    process.exit(1);
  }
}

// Execute anchoring
main()
  .then((result) => {
    console.log("\n🎉 Anchoring complete!");
    console.log("📋 Summary:", JSON.stringify(result, null, 2));
    process.exit(0);
  })
  .catch((error) => {
    console.error("❌ Script failed:", error);
    process.exit(1);
  });
