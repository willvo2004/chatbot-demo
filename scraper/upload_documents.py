import os
import sys
import logging
from uploader import ProductBlobUploader

# Configure logging
logging.basicConfig(level=logging.INFO)


def upload_documents(connection_string, directory_path):
    uploader = ProductBlobUploader(connection_string=connection_string)

    if not os.path.isdir(directory_path):
        print(f"Directory {directory_path} does not exist")

    results = uploader.process_directory(directory_path)

    print("Upload complete:")
    print(f"  Successfully uploaded: {len(results['successful'])} files")
    if results["successful"]:
        for f in results["successful"]:
            print(f"    - {f}")

    print(f"  Failed to upload: {len(results['failed'])} files")
    if results["failed"]:
        for f in results["failed"]:
            print(f"    - {f}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python upload_documents.py <connection_string> <directory_path>")
        sys.exit(1)

    connection_string = sys.argv[1]
    directory_path = sys.argv[2]

    if not os.path.isdir(directory_path):
        print(f"Directory {directory_path} does not exist.")
        sys.exit(1)

    # Create an instance of the uploader
    uploader = ProductBlobUploader(connection_string=connection_string)

    # Upload all .json files in the specified directory
    results = uploader.process_directory(directory_path)

    # Print summary
    print("Upload complete:")
    print(f"  Successfully uploaded: {len(results['successful'])} files")
    if results["successful"]:
        for f in results["successful"]:
            print(f"    - {f}")

    print(f"  Failed to upload: {len(results['failed'])} files")
    if results["failed"]:
        for f in results["failed"]:
            print(f"    - {f}")


if __name__ == "__main__":
    main()
