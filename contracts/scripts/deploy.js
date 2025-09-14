const { ethers } = require("hardhat");

async function main() {
  console.log("🚀 Deploying ComplianceAnchor contract...");
  
  // Get the contract factory
  const ComplianceAnchor = await ethers.getContractFactory("ComplianceAnchor");
  
  // Deploy the contract
  const complianceAnchor = await ComplianceAnchor.deploy();
  
  // Wait for deployment
  await complianceAnchor.waitForDeployment();
  
  const contractAddress = await complianceAnchor.getAddress();
  const deployerAddress = await complianceAnchor.owner();
  
  console.log("✅ ComplianceAnchor deployed successfully!");
  console.log(`📍 Contract Address: ${contractAddress}`);
  console.log(`👤 Owner Address: ${deployerAddress}`);
  console.log(`🌐 Network: ${hre.network.name}`);
  
  // Verify contract version
  const version = await complianceAnchor.version();
  console.log(`📦 Contract Version: ${version}`);
  
  // Save deployment info to file
  const fs = require("fs");
  const deploymentInfo = {
    contractAddress: contractAddress,
    owner: deployerAddress,
    network: hre.network.name,
    deployedAt: new Date().toISOString(),
    version: version
  };
  
  fs.writeFileSync(
    "deployment.json", 
    JSON.stringify(deploymentInfo, null, 2)
  );
  
  console.log("💾 Deployment info saved to deployment.json");
  
  // Instructions for next steps
  console.log("\n📋 Next Steps:");
  console.log(`1. Set CONTRACT_ADDRESS=${contractAddress} in your .env file`);
  console.log(`2. Test anchoring: node scripts/anchor.js --root 0x1234...`);
  console.log(`3. Update backend polygon_anchor.py with contract address`);
  
  return contractAddress;
}

// Execute deployment
main()
  .then((address) => {
    console.log(`\n🎉 Deployment complete! Contract address: ${address}`);
    process.exit(0);
  })
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });
