from flask import Flask, jsonify, g, request, render_template
from hedera import (
    Client, PrivateKey, AccountBalanceQuery,
    AccountId, ContractCallQuery, ContractExecuteTransaction,
    ContractFunctionParameters, ContractId, ContractCreateTransaction
)
import os
import logging
import json
from functools import wraps
from dotenv import load_dotenv
import jpype

# --------------------------
# Initial Setup
# --------------------------

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)

# --------------------------
# Hedera Configuration
# --------------------------

def initialize_hedera():
    """Initialize Hedera components with emoji status checks"""
    # Verify credentials
    HEDERA_ACCOUNT_ID = os.getenv("HEDERA_ACCOUNT_ID")
    HEDERA_PRIVATE_KEY = os.getenv("HEDERA_PRIVATE_KEY")
    ELECTION_CONTRACT_ID = os.getenv("ELECTION_CONTRACT_ID")

    if not all([HEDERA_ACCOUNT_ID, HEDERA_PRIVATE_KEY]):
        logger.error("❌ Missing Hedera credentials in .env file!")
        return False

    logger.info(f"✅ HEDERA_ACCOUNT_ID: {HEDERA_ACCOUNT_ID}")
    logger.info(f"✅ HEDERA_PRIVATE_KEY: {HEDERA_PRIVATE_KEY[:10]}...")

    # Initialize JVM if needed
    if not jpype.isJVMStarted():
        try:
            jpype.startJVM()
            logger.info("✅ JVM started successfully")
        except Exception as e:
            logger.error(f"❌ JVM initialization failed: {str(e)}")
            return False

    return True

if not initialize_hedera():
    logger.error("🛑 Critical initialization failed - check logs above")

# --------------------------
# Hedera Manager Class
# --------------------------

class HederaManager:
    @staticmethod
    def get_client():
        """Get or create Hedera client with connection check"""
        if not hasattr(g, 'hedera_client'):
            try:
                client = Client.forTestnet()
                operator_id = AccountId.fromString(os.getenv("HEDERA_ACCOUNT_ID"))
                operator_key = PrivateKey.fromString(os.getenv("HEDERA_PRIVATE_KEY"))
                client.setOperator(operator_id, operator_key)
                
                # Verify connection
                balance = AccountBalanceQuery().setAccountId(operator_id).execute(client)
                logger.info(f"💰 Account balance: {balance.hbars.toString()}")
                
                g.hedera_client = client
                logger.info("✅ Hedera client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Hedera client: {str(e)}")
                g.hedera_client = None
        return g.hedera_client

    @staticmethod
    def get_contract():
        """Get contract ID with validation"""
        contract_id = os.getenv("ELECTION_CONTRACT_ID")
        if not contract_id:
            logger.error("⚠️ ELECTION_CONTRACT_ID not set in .env!")
            raise ValueError("Contract ID missing")
        
        if not contract_id.startswith("0.0."):
            logger.error("❌ Invalid contract ID format")
            raise ValueError("Invalid contract ID format")
            
        return ContractId.fromString(contract_id)

# --------------------------
# Contract Interaction
# --------------------------

def execute_contract_function(function_name, params=None):
    """Execute a contract function with error handling"""
    try:
        client = HederaManager.get_client()
        contract_id = HederaManager.get_contract()
        
        tx = (ContractExecuteTransaction()
             .setContractId(contract_id)
             .setGas(1000000)
             .setFunction(function_name, params or ContractFunctionParameters())
             .execute(client))
        
        receipt = tx.getReceipt(client)
        logger.info(f"📝 {function_name} TX: {receipt.transactionId.toString()}")
        return receipt
        
    except Exception as e:
        logger.error(f"❌ Contract execution failed: {str(e)}")
        raise

def query_contract(function_name, params=None):
    """Query contract state with error handling"""
    try:
        client = HederaManager.get_client()
        contract_id = HederaManager.get_contract()
        
        query = (ContractCallQuery()
                .setContractId(contract_id)
                .setGas(100000)
                .setFunction(function_name, params or ContractFunctionParameters()))
        
        return query.execute(client)
        
    except Exception as e:
        logger.error(f"❌ Contract query failed: {str(e)}")
        raise

# --------------------------
# Flask Routes
# --------------------------

@app.route("/election")
@handle_hedera_errors
def election_dashboard():
    """Main election dashboard"""
    candidates = []
    try:
        count = query_contract("candidatesCount").getUint256(0)
        for i in range(1, count + 1):
            name, votes = query_contract(
                "getCandidate",
                ContractFunctionParameters().addUint256(i)
            )
            candidates.append({"id": i, "name": name, "votes": votes})
        
        winner_name, winner_votes = query_contract("getWinner")
        
        return render_template("election.html",
                            candidates=candidates,
                            winner=winner_name,
                            total_votes=winner_votes)
    
    except Exception as e:
        logger.error(f"❌ Dashboard error: {str(e)}")
        return render_template("error.html", error=str(e))

@app.route("/election/vote", methods=["POST"])
@handle_hedera_errors
def vote():
    """Handle voting"""
    data = request.get_json()
    if not data or "candidate_id" not in data:
        return jsonify({"error": "❌ Missing candidate ID"}), 400
    
    try:
        receipt = execute_contract_function(
            "vote",
            ContractFunctionParameters().addUint256(int(data["candidate_id"]))
        
        return jsonify({
            "status": "✅ Vote recorded",
            "tx_id": str(receipt.transactionId),
            "hashscan_url": f"https://hashscan.io/testnet/transaction/{receipt.transactionId}"
        })
    
    except Exception as e:
        logger.error(f"❌ Vote failed: {str(e)}")
        return jsonify({"error": f"❌ {str(e)}"}), 500

# --------------------------
# Admin Routes
# --------------------------

@app.route("/election/admin/add_candidate", methods=["POST"])
@handle_hedera_errors
def add_candidate():
    """Admin: Add new candidate"""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "❌ Missing candidate name"}), 400
    
    try:
        receipt = execute_contract_function(
            "addCandidate",
            ContractFunctionParameters().addString(data["name"]))
        
        return jsonify({
            "status": "✅ Candidate added",
            "tx_id": str(receipt.transactionId),
            "candidate": data["name"]
        })
    
    except Exception as e:
        logger.error(f"❌ Add candidate failed: {str(e)}")
        return jsonify({"error": f"❌ {str(e)}"}), 500

# --------------------------
# Main Execution
# --------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)