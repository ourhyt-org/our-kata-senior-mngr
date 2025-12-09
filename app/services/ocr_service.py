import boto3
from typing import List

textract = boto3.client("textract")


def extract_text_from_image(image_bytes: bytes) -> str:
    response = textract.detect_document_text(
        Document={"Bytes": image_bytes}
    )

    lines: List[str] = []
    for block in response.get("Blocks", []):
        if block.get("BlockType") == "LINE":
            lines.append(block["Text"])

    return "\n".join(lines)