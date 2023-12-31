from django.http import JsonResponse
import socket
import json
import logging
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import pymongo
import certifi

# Configure logging
logger = logging.getLogger(__name__)


@csrf_exempt
def adcs_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Unsupported request method."}, status=405)

    try:
        client = pymongo.MongoClient(
            "",
            tlsCAFile=certifi.where(),
        )
        db = client.myDatabase
        collection = db.adcs_collection

        # Parse the request data
        request_data = json.loads(request.body)
        text_to_send = request_data.get("command", "default command")

        # Validate the input data
        if not text_to_send:
            return JsonResponse({"error": "Invalid request data."}, status=400)

        # Define the server address from Django settings
        server_address = (settings.SERVER_HOST, settings.SERVER_PORT)

        logger.info(f"Connecting to {server_address}...")

        # Using a context manager for socket operations
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect(server_address)

            formatted_data = f"{10},{5},{text_to_send}"
            client_socket.send(formatted_data.encode("utf-8"))

            # Wait for and receive acknowledgment from the server
            acknowledgment = client_socket.recv(1024)

            # Ensure acknowledgment data is in JSON format
            try:
                acknowledgment_data = json.loads(acknowledgment.decode("utf-8"))
                if not isinstance(acknowledgment_data, dict):
                    raise ValueError("Acknowledgment data is not a dictionary")
            except (json.JSONDecodeError, ValueError) as e:
                return JsonResponse(
                    {"error": f"Invalid acknowledgment format: {str(e)}"}, status=500
                )

            # Insert the acknowledgment data into MongoDB
            result = collection.insert_one(acknowledgment_data)

            # Return the server's acknowledgment to the frontend
            if result:
                return JsonResponse({"message": "Data inserted successfully"})
            else:
                return JsonResponse({"message": "Error during insertion"})

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing request data: {str(e)}")
        return JsonResponse({"error": "Invalid JSON data."}, status=400)
    except socket.error as e:
        logger.error(f"Socket error: {str(e)}")
        return JsonResponse({"error": "Error connecting to the server."}, status=500)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)


@csrf_exempt
def fetch_telemetry(request):
    if request.method != "GET":
        return JsonResponse({"error": "Unsupported request method."}, status=405)

    client = pymongo.MongoClient(
        "mongodb+srv://merradi:sonxoq-xubfi5-tyxPas@cluster0.uwxph0t.mongodb.net/?retryWrites=true&w=majority",
        tlsCAFile=certifi.where(),
    )
    db = client.myDatabase
    collection = db.adcs_collection

    # Fetch housekeeping data from MongoDB
    documents = collection.find({"housekeeping_data": {"$exists": True}})

    # Prepare the dataset
    hk_data = [
        {
            "timestamp": doc["housekeeping_data"]["timestamp"],
            "temperature": doc["housekeeping_data"]["temperature"],
            "power_usage": doc["housekeeping_data"]["power_usage"],
            "orientation": doc["housekeeping_data"]["orientation"],
        }
        for doc in documents
    ]

    # Return the dataset
    return JsonResponse({"hk_data": hk_data})


@csrf_exempt
def fetch_operational(request):
    if request.method != "GET":
        return JsonResponse({"error": "Unsupported request method."}, status=405)

    client = pymongo.MongoClient(
        "mongodb+srv://merradi:sonxoq-xubfi5-tyxPas@cluster0.uwxph0t.mongodb.net/?retryWrites=true&w=majority",
        tlsCAFile=certifi.where(),
    )
    db = client.myDatabase
    collection = db.adcs_collection

    # Fetch command data from MongoDB
    documents = collection.find({"command_data": {"$exists": True}})

    # Prepare the dataset
    cmd_data = [
        {
            "timestamp": doc["command_data"]["timestamp"],
            "position": doc["command_data"]["position"],
            "velocity": doc["command_data"]["velocity"],
            "maneuver_count": doc["command_data"]["maneuver_count"],
        }
        for doc in documents
    ]

    # Return the dataset
    return JsonResponse({"cmd_data": cmd_data})
