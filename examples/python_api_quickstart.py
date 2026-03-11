from akf import Pipeline


# Minimal Python API quickstart.
def main() -> None:
    pipeline = Pipeline(output="./output")
    result = pipeline.generate("Create a guide on API rate limiting")

    print(f"success={result.success}")
    print(f"path={result.file_path}")
    print(f"attempts={result.attempts}")


if __name__ == "__main__":
    main()
