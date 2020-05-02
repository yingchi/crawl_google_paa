import os
import pandas as pd

# df = pd.read_csv("input/phrases_interview.csv", header=None, names=["Phrase"])
df = pd.read_csv("input/phrases.csv", header=0)

TITLES = [
    "firefighter",
    "substitute teacher",
    "dental hygienist",
    "teacher",
    "licensed practical nurse",
    "dental assistant",
    "nursing assistant",
    "surgical technician",
]

# TITLES = ["teacher", "project manager", "business analyst", "accountant", "administrative assistant", "product manager"]

for TITLE in TITLES[-1:]:
    df["query"] = df.apply(lambda x: x["Phrase"].replace("{keyword}", TITLE), axis=1)
    input_file = "input/faq_queries_{}.csv".format(TITLE.lower().replace(" ", "_"))
    df[["query"]].to_csv(input_file, index=False, header=False)
    output_fs_file = "output/fs_" + TITLE.lower().replace(" ", "_") + ".csv"
    output_paa_file = "output/paa_" + TITLE.lower().replace(" ", "_") + ".csv"
    command = """poetry run python google_paa.py query {} --output_paa={} --output_fs={} --headless --cleantext --num=10""".format(
        input_file, output_paa_file, output_fs_file
    )
    os.system(command)
