from flask import Flask, jsonify, request, render_template
from web3 import Web3
import os
from flask_cors import CORS
from dotenv import load_dotenv
import datetime

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
@app.route('/results')
def results():
    return render_template('results.html')  # This serves the results.html file

@app.route('/results/data')
def results_data():
    try:
        candidates = []
        total_candidates = contract.functions.candidatesCount().call()
        
        # Get all candidates with their vote counts
        for candidate_id in range(1, total_candidates + 1):
            name, votes = contract.functions.getCandidate(candidate_id).call()
            candidates.append({
                'id': candidate_id,
                'name': name,
                'votes': votes
            })
        
        # Determine winner(s) - handles ties
        max_votes = max(c['votes'] for c in candidates)
        winners = [c for c in candidates if c['votes'] == max_votes]
        
        return jsonify({
            'success': True,
            'candidates': sorted(candidates, key=lambda x: x['votes'], reverse=True),
            'winners': winners,
            'total_votes': sum(c['votes'] for c in candidates),
            'timestamp': datetime.datetime.now().isoformat()
        })
    
    except Exception as e:
        app.logger.error(f"Error fetching results: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch election results',
            'details': str(e)
        }), 500
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
@app.route("/has-voted", methods=["GET"])
def has_voted():
    address = request.args.get("address")
    if not address or not web3.is_address(address):
        return jsonify({"error": "Invalid address"}), 400
    
    checksum_address = Web3.to_checksum_address(address)
    
    try:
        has_voted, voted_candidate_id = contract.functions.voters(checksum_address).call()
        if has_voted:
            return jsonify({
                "hasVoted": True,
                "candidateId": voted_candidate_id
            })
        else:
            return jsonify({
                "hasVoted": False,
                "candidateId": None
            })
    except Exception as e:
        return jsonify({
            "error": "Failed to check voter status",
            "details": str(e)
        }), 500

@app.route("/vote", methods=["GET", "POST"])
def vote():
    if request.method == "GET":
        # Serve the voting page
        return render_template("vote.html")
    
    elif request.method == "POST":
        try:
            # Validate request has JSON data
            if not request.is_json:
                return jsonify({"error": "Request must be JSON"}), 400

            data = request.get_json()
            app.logger.info(f"Received vote data: {data}")

            # Validate required fields
            required_fields = ['candidate_id', 'user_address']
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400

            # Validate candidate_id
            try:
                candidate_id = int(data['candidate_id'])
                if candidate_id <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                return jsonify({"error": "candidate_id must be a positive integer"}), 400

            # Validate user_address
            user_address = data['user_address']
            if not web3.is_address(user_address):
                return jsonify({"error": "Invalid Ethereum address"}), 400

            checksum_address = Web3.to_checksum_address(user_address)

            # Check if already voted
            try:
                has_voted = contract.functions.voters(checksum_address).call()[0]
                if has_voted:
                    return jsonify({"error": "You have already voted"}), 400
            except Exception as e:
                app.logger.error(f"Voter check failed: {str(e)}")
                return jsonify({"error": "Failed to check voter status"}), 500

            # Build transaction (frontend will sign with MetaMask)
            try:
                txn_data = contract.functions.vote(candidate_id).build_transaction({
                    'from': checksum_address,
                    'gas': 200000,  # Fixed gas or estimate properly
                    'gasPrice': web3.eth.gas_price,
                    'nonce': web3.eth.get_transaction_count(checksum_address),
                })

                return jsonify({
                    "status": "sign_required",
                    "txn_data": {
                        "to": txn_data['to'],
                        "data": txn_data['data'],
                        "value": "0x0",  # No ETH transfer
                        "gas": web3.to_hex(txn_data['gas']),
                        "gasPrice": web3.to_hex(txn_data['gasPrice']),
                    }
                })

            except ValueError as ve:
                app.logger.error(f"Transaction validation error: {str(ve)}")
                return jsonify({"error": "Invalid transaction parameters"}), 400
            except Exception as e:
                app.logger.error(f"Voting transaction failed: {str(e)}")
                return jsonify({"error": "Failed to process vote"}), 500

        except Exception as e:
            app.logger.error(f"Unexpected error in vote endpoint: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500
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
            txn_data = contract.functions.vote(candidate_id).build_transaction({
    'from': checksum_address,
    'gas': 200000,
    'gasPrice': web3.eth.gas_price,
    'nonce': web3.eth.get_transaction_count(checksum_address),
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
            print(f"Received vote for candidate ID {candidate_id} from {user_address}")
            
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
