from flask import Flask, render_template, jsonify, request, g
from hedera import (
    Client, PrivateKey, AccountId,
    ContractCallQuery, ContractExecuteTransaction,
    ContractFunctionParameters, ContractId
)
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Hedera Manager (from your existing code)
class HederaManager:
    @staticmethod
    def get_client():
        if not hasattr(g, 'hedera_client'):
            try:
                client = Client.forTestnet()
                operator_id = AccountId.fromString(os.getenv("HEDERA_ACCOUNT_ID"))
                operator_key = PrivateKey.fromString(os.getenv("HEDERA_PRIVATE_KEY"))
                client.setOperator(operator_id, operator_key)
                g.hedera_client = client
            except Exception as e:
                print(f"Hedera client init failed: {str(e)}")
                g.hedera_client = None
        return g.hedera_client

# Election Contract Interface
class ElectionContract:
    CONTRACT_ID = None  # Set after deployment

    @classmethod
    def deploy(cls, client):
        # Load your compiled contract bytecode here
        with open("Election.bin", "rb") as f:
            bytecode = f.read()
        
        tx = ContractCreateTransaction().setBytecode(bytecode).execute(client)
        receipt = tx.getReceipt(client)
        cls.CONTRACT_ID = receipt.contractId
        return cls.CONTRACT_ID

    @classmethod
    def add_candidate(cls, client, name):
        tx = (ContractExecuteTransaction()
             .setContractId(cls.CONTRACT_ID)
             .setGas(100000)
             .setFunction("addCandidate", 
                 ContractFunctionParameters().addString(name))
             .execute(client))
        return tx.getReceipt(client)

    @classmethod
    def register_voter(cls, client, voter_address):
        tx = (ContractExecuteTransaction()
             .setContractId(cls.CONTRACT_ID)
             .setGas(100000)
             .setFunction("registerVoter",
                 ContractFunctionParameters().addAddress(voter_address))
             .execute(client))
        return tx.getReceipt(client)

    @classmethod
    def vote(cls, client, candidate_id):
        tx = (ContractExecuteTransaction()
             .setContractId(cls.CONTRACT_ID)
             .setGas(100000)
             .setFunction("vote",
                 ContractFunctionParameters().addUint256(candidate_id))
             .execute(client))
        return tx.getReceipt(client)

    @classmethod
    def get_winner(cls, client):
        result = (ContractCallQuery()
                .setContractId(cls.CONTRACT_ID)
                .setGas(100000)
                .setFunction("getWinner")
                .execute(client))
        return (result.getString(0), result.getUint256(1))

    @classmethod
    def get_candidate(cls, client, candidate_id):
        result = (ContractCallQuery()
                .setContractId(cls.CONTRACT_ID)
                .setGas(100000)
                .setFunction("getCandidate",
                    ContractFunctionParameters().addUint256(candidate_id))
                .execute(client))
        return (result.getString(0), result.getUint256(1))

    @classmethod
    def is_voter_registered(cls, client, voter_address):
        result = (ContractCallQuery()
                .setContractId(cls.CONTRACT_ID)
                .setGas(100000)
                .setFunction("isVoterRegistered",
                    ContractFunctionParameters().addAddress(voter_address))
                .execute(client))
        return result.getBool(0)

# Flask Routes
@app.route("/election")
def election_dashboard():
    return render_template("election_dashboard.html")

@app.route("/election/deploy", methods=["POST"])
def deploy_contract():
    client = HederaManager.get_client()
    if not client:
        return jsonify({"error": "Hedera client unavailable"}), 503
    
    contract_id = ElectionContract.deploy(client)
    return jsonify({
        "status": "success",
        "contract_id": str(contract_id)
    })

@app.route("/election/add_candidate", methods=["POST"])
def add_candidate():
    client = HederaManager.get_client()
    data = request.get_json()
    
    receipt = ElectionContract.add_candidate(client, data["name"])
    return jsonify({
        "status": "success",
        "tx_id": str(receipt.transactionId),
        "candidate_name": data["name"]
    })

@app.route("/election/register", methods=["POST"])
def register_voter():
    client = HederaManager.get_client()
    data = request.get_json()
    
    receipt = ElectionContract.register_voter(client, data["voter_address"])
    return jsonify({
        "status": "success",
        "tx_id": str(receipt.transactionId),
        "voter_address": data["voter_address"]
    })

@app.route("/election/vote", methods=["POST"])
def submit_vote():
    client = HederaManager.get_client()
    data = request.get_json()
    
    receipt = ElectionContract.vote(client, data["candidate_id"])
    return jsonify({
        "status": "success",
        "tx_id": str(receipt.transactionId),
        "candidate_id": data["candidate_id"]
    })

@app.route("/election/results")
def get_results():
    client = HederaManager.get_client()
    
    winner_name, winner_votes = ElectionContract.get_winner(client)
    return jsonify({
        "winner": winner_name,
        "votes": winner_votes
    })

if __name__ == "__main__":
    app.run(debug=True)