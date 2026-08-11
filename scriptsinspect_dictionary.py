import webdataset as wds

URL = (
    "https://huggingface.co/datasets/"
    "bridgeconn/sign-dictionary-isl/resolve/main/"
    "shard_{00001..00002}-train.tar"
)

dataset = wds.WebDataset(
    URL,
    shardshuffle=False
).decode()

for sample in dataset:

    metadata = sample["json"]

    print("=" * 70)

    print("Filename:")
    print(metadata.get("filename"))

    print("\nTranscript:")
    print(metadata.get("transcripts"))

    print("\nGloss:")
    print(metadata.get("glosses"))

    print("\nAvailable data:")
    print(sample.keys())

    break