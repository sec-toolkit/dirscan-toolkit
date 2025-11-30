import datetime
import json

import sarif_om as sarif
from sarif_om import *


def to_json(results):
    """results:list[dict] -> str"""
    return json.dumps(results, ensure_ascii=False, indent=2)


def to_sarif(results, output_file):
    """
    results: list[dict] 每个dict至少有{'url':'...','status': 200}
    output_file: 写出的 *.sarif路径
    """
    driver = ToolComponent(
        name="dirscan",
        version="0.1.0",
    )
    tool = Tool(driver=driver)
    run = Run(tool=tool, results=[])
    for r in results:
        run.results.append(
            Result(
                rule_id="dirscan/leak",
                level="warning",
                message={"text": f"{r['url']} -> {r['status']}"},
                locations=[
                    PhysicalLocation(artifact_location=ArtifactLocation(uri=r["url"]))
                ],
            )
        )
    log = SarifLog(version="2.1.0", runs=[run])
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(
            json.dumps(log, default=lambda o: o.__dict__, ensure_ascii=False, indent=2)
        )
