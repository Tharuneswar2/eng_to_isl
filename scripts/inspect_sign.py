import tarfile
import json
from pathlib import Path

tar_path = Path(
    "data/sign_dictionary/shard_00001-train.tar"
)

with tarfile.open(tar_path, "r") as tar:

    members = tar.getmembers()

    print("Total files:", len(members))

    # Find first JSON
    json_member = next(
        m for m in members
        if m.name.endswith(".json")
    )

    print("\nJSON file:")
    print(json_member.name)

    file_obj = tar.extractfile(json_member)

    data = json.load(file_obj)

    print("\nJSON CONTENT:")
    print(json.dumps(data, indent=2))

    print("\nFiles belonging to this sample:")

    sample_id = json_member.name.rsplit(".", 1)[0]

    for member in members:

        if member.name.startswith(sample_id):

            print(
                member.name,
                member.size,
                "bytes"
            )