const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ComplianceAnchor", function () {
  let complianceAnchor;
  let owner;
  let addr1;
  let addr2;

  beforeEach(async function () {
    // Get signers
    [owner, addr1, addr2] = await ethers.getSigners();
    
    // Deploy contract
    const ComplianceAnchor = await ethers.getContractFactory("ComplianceAnchor");
    complianceAnchor = await ComplianceAnchor.deploy();
    await complianceAnchor.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should set the right owner", async function () {
      expect(await complianceAnchor.owner()).to.equal(owner.address);
    });

    it("Should return correct version", async function () {
      expect(await complianceAnchor.version()).to.equal("1.0.0");
    });
  });

  describe("Root Anchoring", function () {
    const testRoot = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef";
    
    it("Should anchor a root and emit RootAnchored event", async function () {
      const tx = await complianceAnchor.anchorRoot(testRoot);
      const receipt = await tx.wait();
      
      // Check event emission
      const events = receipt.logs.map(log => {
        try {
          return complianceAnchor.interface.parseLog(log);
        } catch (error) {
          return null;
        }
      }).filter(event => event !== null);
      
      expect(events.length).to.equal(1);
      expect(events[0].name).to.equal("RootAnchored");
      expect(events[0].args.root).to.equal(testRoot);
      expect(events[0].args.by).to.equal(owner.address);
      expect(events[0].args.timestamp).to.be.a("bigint");
    });

    it("Should allow any address to anchor a root", async function () {
      const tx = await complianceAnchor.connect(addr1).anchorRoot(testRoot);
      const receipt = await tx.wait();
      
      const events = receipt.logs.map(log => {
        try {
          return complianceAnchor.interface.parseLog(log);
        } catch (error) {
          return null;
        }
      }).filter(event => event !== null);
      
      expect(events[0].args.by).to.equal(addr1.address);
    });

    it("Should reject zero root hash", async function () {
      const zeroRoot = "0x0000000000000000000000000000000000000000000000000000000000000000";
      
      await expect(
        complianceAnchor.anchorRoot(zeroRoot)
      ).to.be.revertedWith("Root cannot be zero");
    });

    it("Should handle multiple root anchoring", async function () {
      const root1 = "0x1111111111111111111111111111111111111111111111111111111111111111";
      const root2 = "0x2222222222222222222222222222222222222222222222222222222222222222";
      
      // Anchor first root
      const tx1 = await complianceAnchor.anchorRoot(root1);
      const receipt1 = await tx1.wait();
      
      // Anchor second root
      const tx2 = await complianceAnchor.anchorRoot(root2);
      const receipt2 = await tx2.wait();
      
      // Both should succeed
      expect(receipt1.status).to.equal(1);
      expect(receipt2.status).to.equal(1);
    });
  });

  describe("Owner-only functions", function () {
    const testRoot = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef";
    
    it("Should allow owner to use anchorRootOwnerOnly", async function () {
      const tx = await complianceAnchor.anchorRootOwnerOnly(testRoot);
      const receipt = await tx.wait();
      
      expect(receipt.status).to.equal(1);
    });

    it("Should reject non-owner from using anchorRootOwnerOnly", async function () {
      await expect(
        complianceAnchor.connect(addr1).anchorRootOwnerOnly(testRoot)
      ).to.be.revertedWith("Only owner can call this function");
    });

    it("Should allow owner to transfer ownership", async function () {
      await complianceAnchor.transferOwnership(addr1.address);
      expect(await complianceAnchor.owner()).to.equal(addr1.address);
    });

    it("Should reject non-owner from transferring ownership", async function () {
      await expect(
        complianceAnchor.connect(addr1).transferOwnership(addr2.address)
      ).to.be.revertedWith("Only owner can call this function");
    });

    it("Should reject zero address in ownership transfer", async function () {
      await expect(
        complianceAnchor.transferOwnership(ethers.ZeroAddress)
      ).to.be.revertedWith("New owner cannot be zero address");
    });
  });

  describe("Gas optimization", function () {
    it("Should use minimal gas for anchoring", async function () {
      const testRoot = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef";
      
      const tx = await complianceAnchor.anchorRoot(testRoot);
      const receipt = await tx.wait();
      
      // Gas should be reasonable (less than 50k for a simple anchor)
      expect(receipt.gasUsed).to.be.lessThan(50000);
      console.log(`    ⛽ Gas used for anchoring: ${receipt.gasUsed}`);
    });
  });

  describe("Event indexing", function () {
    it("Should emit events with proper indexing", async function () {
      const testRoot = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef";
      
      await expect(complianceAnchor.anchorRoot(testRoot))
        .to.emit(complianceAnchor, "RootAnchored")
        .withArgs(testRoot, await time.latest() + 1, owner.address);
    });
  });
});
