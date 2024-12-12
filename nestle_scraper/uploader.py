from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from azure.core.exceptions import ResourceExistsError
from typing import Dict, List
import asyncio
import os
import logging


class ProductBlobUploader:
    def __init__(self, connection_string: str, container_name: str = "products", batch_size: int = 100):
        self.blob_service = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = container_name
        self.batch_size = batch_size
        # Note: Creating the container should also be done async if using aio clients
        # so you might have to do it in an async method
        # Or create a synchronous container outside of this if you must.

    async def _ensure_container(self) -> ContainerClient:
        try:
            container_client = self.blob_service.get_container_client(self.container_name)
            await container_client.create_container()
        except ResourceExistsError:
            pass
        return self.blob_service.get_container_client(self.container_name)

    async def initialize(self):
        self.container_client = await self._ensure_container()

    async def upload_file(self, file_path: str) -> bool:
        try:
            blob_name = os.path.basename(file_path)
            async with self.container_client as cc:  # ensure client context
                with open(file_path, "rb") as data:
                    await cc.upload_blob(name=blob_name, data=data, overwrite=True)
            return True
        except Exception as e:
            logging.error(f"Error uploading {file_path}: {str(e)}")
            return False

    async def upload_batch(self, file_paths: List[str]) -> Dict[str, bool]:
        tasks = [self.upload_file(file_path) for file_path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return dict(zip(file_paths, results))

    def process_directory(self, directory_path: str) -> Dict[str, List[str]]:
        # This part remains similar, but remember that upload_batch is async
        # so we call it with asyncio.run()
        success_files = []
        failed_files = []

        json_files = [os.path.join(directory_path, f) for f in os.listdir(directory_path) if f.endswith(".json")]

        # Ensure container exists
        asyncio.run(self.initialize())

        for i in range(0, len(json_files), self.batch_size):
            batch = json_files[i : i + self.batch_size]

            results = asyncio.run(self.upload_batch(batch))

            for file_path, success in results.items():
                if isinstance(success, Exception):
                    failed_files.append(file_path)
                elif success:
                    success_files.append(file_path)
                else:
                    failed_files.append(file_path)

            logging.info(
                f"Processed batch {i//self.batch_size + 1}: "
                f"{len(success_files)} successful, {len(failed_files)} failed"
            )

        return {"successful": success_files, "failed": failed_files}
