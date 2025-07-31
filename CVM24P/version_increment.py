import fileinput


def version_increment():
    with fileinput.input(files="pyproject.toml", encoding="utf-8", inplace=True) as f:
        for line in f:
            if "version" in line:
                version = line.split('"')[1].strip()
                version = version.split(".")
                version[-1] = str(int(version[-1]) + 1)
                version = ".".join(version)
                print(f'version = "{version}"', end="\n")  # Print new version number
            else:
                print(line, end="")  # Print the original line


if __name__ == "__main__":
    version_increment()
