import subprocess
import pymongo
from datetime import datetime
import json
import os  # Import the os module
import pytz  # Import the pytz library
from datetime import datetime, timedelta


# Read image names from the image.txt file in the config folder
image_file_path = "config/image.txt"
try:
    with open(image_file_path, "r") as file:
        image_names = [line.strip() for line in file.readlines()]
except FileNotFoundError:
    print(f"Error: Image file '{image_file_path}' not found.")
    exit(1)

# Connect to MongoDB
client = pymongo.MongoClient("mongodb+srv://ratnesh:ratnesh@cluster0.3ka0uom.mongodb.net/cve_db?retryWrites=true&w=majority")
today_date = datetime.now().strftime("%d-%m-%Y")
collection_name = f"{today_date}_cve_list"
db = client.cve_db
collection = db[collection_name]
collection.delete_many({})

# Define the Indian Standard Time (IST) timezone
ist_timezone = pytz.timezone("Asia/Kolkata")

thirty_days_ago = datetime.now() - timedelta(days=30)

# Get a list of collections in the database
all_collections = db.list_collection_names()

# Iterate over collections and delete those created 30 days ago
for collection_name in all_collections:
    try:
        # Parse the collection name to get the creation date
        collection_date = datetime.strptime(collection_name.split('_')[0], "%d-%m-%Y")

        # Check if the collection is older than 30 days
        if collection_date < thirty_days_ago:
            db[collection_name].drop()
            print(f"Collection {collection_name} deleted. It was created on {collection_date.strftime('%d-%m-%Y')}")
    except ValueError:
        # Skip collections with invalid names (not following the expected date format)
        continue


# Process two images in one go
for i in range(0, len(image_names), 2):
    try:
        # Take two images at a time
        image_name_1 = image_names[i]
        image_name_2 = image_names[i + 1] if i + 1 < len(image_names) else None

        # Get the size of each image
        size_1 = os.path.getsize(image_name_1) / (1024 * 1024) if os.path.exists(image_name_1) else None
        size_2 = os.path.getsize(image_name_2) / (1024 * 1024) if image_name_2 and os.path.exists(image_name_2) else None

        if size_1 is not None:
            print(f"Image size for {image_name_1}: {size_1:.2f} MB")
        else:
            print(f"Unable to determine size for {image_name_1}")

        if image_name_2:
            if size_2 is not None:
                print(f"Image size for {image_name_2}: {size_2:.2f} MB")
            else:
                print(f"Unable to determine size for {image_name_2}")

        # Run Grype for each image and store the output in a variable
        grype_output_1 = subprocess.run(["grype", image_name_1, "-o", "json"], capture_output=True, text=True, check=True)
        grype_output_2 = subprocess.run(["grype", image_name_2, "-o", "json"], capture_output=True, text=True, check=True) if image_name_2 else None

        # Insert the vulnerability counts into MongoDB with IST timestamp
        grype_data_1 = json.loads(grype_output_1.stdout)
        vulnerability_count_1 = len(grype_data_1.get("matches", []))

        grype_data_2 = json.loads(grype_output_2.stdout) if grype_output_2 else None
        vulnerability_count_2 = len(grype_data_2.get("matches", [])) if grype_data_2 else None

        # Get the current time in IST
        current_time_ist = datetime.now(ist_timezone).strftime("%d-%m-%Y %H:%M:%S")

        # Insert vulnerability counts into MongoDB with IST timestamp
        insert_data = {
            "timestamp": current_time_ist,
            "images": [
                {"image": image_name_1, "vulnerability_count": vulnerability_count_1, "size_mb": size_1},
                {"image": image_name_2, "vulnerability_count": vulnerability_count_2, "size_mb": size_2} if image_name_2 else None
            ]
        }

        print(f"Inserting data into MongoDB: {insert_data}")
        collection.insert_one(insert_data)

        print(f"Vulnerabilities found for {image_name_1}: {vulnerability_count_1}")
        if image_name_2:
            print(f"Vulnerabilities found for {image_name_2}: {vulnerability_count_2}")

    except subprocess.CalledProcessError as e:
        print(f"Error running Grype for {image_name_1} or {image_name_2}: {e}")


# import subprocess
# import pymongo
# import json
# from datetime import datetime

# # Read image names from the image.txt file in the config folder
# image_file_path = "config/image.txt"
# try:
#     with open(image_file_path, "r") as file:
#         image_names = [line.strip() for line in file.readlines()]
# except FileNotFoundError:
#     print(f"Error: Image file '{image_file_path}' not found.")
#     exit(1)

# # Connect to MongoDB
# client = pymongo.MongoClient("mongodb+srv://ratnesh:ratnesh@cluster0.3ka0uom.mongodb.net/cve_db?retryWrites=true&w=majority")
# today_date = datetime.now().strftime("%d-%m-%Y")
# collection_name = f"{today_date}_cve_list"
# db = client.cve_db
# collection = db[collection_name]

# for image_name in image_names:
#     try:
#         # Run Grype for each image and store the output in a variable
#         grype_output = subprocess.run(["grype", image_name, "-o", "json"], capture_output=True, text=True, check=True)

#         # Parse Grype output and delete existing data in MongoDB
#         collection.delete_many({"image": image_name})

#         # Insert the new data into MongoDB with epoch timestamp
#         grype_data = json.loads(grype_output.stdout)
#         matches = grype_data.get("matches", [])
#         for match in matches:
#             # Include the image name, epoch timestamp in the MongoDB document
#             match["image"] = image_name
#             match["timestamp"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
#             match["message"] = "Vulnerability found."
#             collection.insert_one(match)

#         if not matches:
#             # Insert a message into MongoDB if no vulnerabilities found
#             collection.insert_one({"image": image_name, "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "message": "No vulnerabilities found."})
#             print(f"No vulnerability matches found in Grype output for {image_name}. Message inserted into MongoDB.")
#         else:
#             print(f"Data inserted into MongoDB for {image_name} successfully, Vulnerability found")
#     except subprocess.CalledProcessError as e:
#         print(f"Error running Grype for {image_name}: {e}")
