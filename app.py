from flask import Flask, jsonify, request, render_template
from web3 import Web3
import os
from flask_cors import CORS
from dotenv import load_dotenv
import pytest
from web3 import Web3

# Make sure your Web3 provider is correctly set
INFURA_URL = "https://sepolia.infura.io/v3/6a7c89a931f74fad9856958a1b69158b"  # Replace with Infura or Hashio RPC URL
web3 = Web3(Web3.HTTPProvider(INFURA_URL))

if not web3.is_connected():
    print("⚠️  Web3 is NOT connected! Check your RPC URL.")
else:
    print("✅ Web3 Connected Successfully!")

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Web3
RPC_URL = os.getenv("RPC_URL")
web3 = Web3(Web3.HTTPProvider(RPC_URL))
CONTRACT_ADDRESS = os.getenv("ELECTION_CONTRACT_ADDRESS")

# Contract ABI
ABI = ABI = [
    {
        "inputs": [
            {
                "internalType": "string",
                "name": "_name",
                "type": "string"
            }
        ],
        "name": "addCandidate",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "id",
                "type": "uint256"
            },
            {
                "indexed": False,
                "internalType": "string",
                "name": "name",
                "type": "string"
            }
        ],
        "name": "CandidateAdded",
        "type": "event"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "_candidateId",
                "type": "uint256"
            }
        ],
        "name": "vote",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "voter",
                "type": "address"
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "candidateId",
                "type": "uint256"
            }
        ],
        "name": "Voted",
        "type": "event"
    },
    {
        "inputs": [],
        "name": "admin",
        "outputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "name": "candidates",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "id",
                "type": "uint256"
            },
            {
                "internalType": "string",
                "name": "name",
                "type": "string"
            },
            {
                "internalType": "uint256",
                "name": "voteCount",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "candidatesCount",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "_candidateId",
                "type": "uint256"
            }
        ],
        "name": "getCandidate",
        "outputs": [
            {
                "internalType": "string",
                "name": "name",
                "type": "string"
            },
            {
                "internalType": "uint256",
                "name": "votes",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getWinner",
        "outputs": [
            {
                "internalType": "string",
                "name": "winnerName",
                "type": "string"
            },
            {
                "internalType": "uint256",
                "name": "winnerVotes",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address"
            }
        ],
        "name": "voters",
        "outputs": [
            {
                "internalType": "bool",
                "name": "hasVoted",
                "type": "bool"
            },
            {
                "internalType": "uint256",
                "name": "votedCandidateId",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Initialize contract
contract = web3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=ABI
)

@app.route("/")
def home():
    return render_template('index.html')

@app.route("/candidates", methods=["GET"])
def get_candidates():
    try:
        candidates = []
        total_candidates = contract.functions.candidatesCount().call()
        for i in range(1, total_candidates + 1):
            name, votes = contract.functions.getCandidate(i).call()
            candidates.append({
                "id": i,
                "name": name,
                "votes": votes
            })
        return jsonify(candidates)
    except Exception as e:
        app.logger.error(f"Error getting candidates: {str(e)}")
        return jsonify({"error": "Failed to fetch candidates"}), 500

@app.route("/vote", methods=["GET", "POST"])
def vote():
    if request.method == "GET":
        return render_template("vote.html")
    
    elif request.method == "POST":
        try:
            data = request.get_json()
            app.logger.info(f"Received vote data: {data}")
            
            # Validate and extract candidate_id
            if 'candidate_id' not in data:
                return jsonify({"error": "Missing candidate_id"}), 400
                
            try:
                candidate_id = int(data['candidate_id'])
            except (TypeError, ValueError):
                return jsonify({"error": "candidate_id must be a number"}), 400
            
            # Validate user_address
            if 'user_address' not in data:
                return jsonify({"error": "Missing user_address"}), 400
                
            user_address = data['user_address']
            if not web3.is_address(user_address):
                return jsonify({"error": "Invalid Ethereum address"}), 400
                
            checksum_address = Web3.to_checksum_address(user_address)
            
            # Check if already voted
            if contract.functions.voters(checksum_address).call()[0]:
                return jsonify({"error": "You have already voted"}), 400
            
            # Submit transaction
            txn_hash = contract.functions.vote(candidate_id).transact({
                'from': checksum_address,
                'gas': 500000,
                'gasPrice': web3.to_wei('20', 'gwei')
            })
            
            # Wait for confirmation
            receipt = web3.eth.wait_for_transaction_receipt(txn_hash)
            
            if receipt.status == 0:
                return jsonify({"error": "Transaction reverted"}), 400
                
            return jsonify({
                "status": "success",
                "txn_hash": txn_hash.hex(),
                "block": receipt.blockNumber
            })
            
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            app.logger.error(f"Voting error: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

@app.route("/winner", methods=["GET"])
def get_winner():
    try:
        name, votes = contract.functions.getWinner().call()
        return jsonify({
            "winner": name,
            "votes": votes
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)