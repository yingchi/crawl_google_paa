import os
import sys
import pandas as pd

# df = pd.read_csv("input/phrases_interview.csv", header=None, names=["Phrase"])
df = pd.read_csv("input/phrases.csv", header=0)
TITLES = [line.rstrip("\n") for line in open("input/titles.csv")]
# TITLES = [
#     "firefighter",
#     "substitute teacher",
#     "dental hygienist",
#     "teacher",
#     "licensed practical nurse",
#     "dental assistant",
#     "nursing assistant",
#     "surgical technician",
# ]

# TITLES = ["teacher", "project manager", "business analyst", "accountant", "administrative assistant", "product manager"]

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        low = int(sys.argv[1])
        high = int(sys.argv[2])
    else:
        low = 0
        high = len(TITLES)
    for TITLE in TITLES[low:high]:
        df["query"] = df.apply(lambda x: x["Phrase"].replace("{keyword}", TITLE), axis=1)
        input_file = "input/faq_queries_{}.csv".format(TITLE.lower().replace(" ", "_"))
        df[["query"]].to_csv(input_file, index=False, header=False)
        output_fs_file = "output/fs_" + TITLE.lower().replace(" ", "_") + ".csv"
        output_paa_file = "output/paa_" + TITLE.lower().replace(" ", "_") + ".csv"
        command = """poetry run python google_paa.py query {} --output_paa={} --skip-fs --headless --cleantext --num=10""".format(
            input_file, output_paa_file
        )
        os.system(command)
