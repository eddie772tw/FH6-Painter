#!/usr/bin/env python3
"""報表生成模組 — HTML 效能報表與 JSON 結果檔。"""

import json
import platform
import time


def generate_json_result(output_path, leaderboard, system_info):
    """輸出純文字 JSON 結果檔 (benchmark_result.json)。"""
    try:
        json_output = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system_info": system_info,
            "leaderboard": [
                {
                    "rank": rank,
                    "id": entry["id"],
                    "name": entry["name"],
                    "weighted_score": int(entry["weighted_score"]),
                    "tiers": {
                        t_name: {
                            "throughput": float(t_data["throughput"]),
                            "score": int(t_data["score"]),
                        }
                        for t_name, t_data in entry["tiers"].items()
                    },
                }
                for rank, entry in enumerate(leaderboard, 1)
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=2)
        print(f"[Storage] JSON result successfully exported to: {output_path}")
    except Exception as e:
        print(f"[Warning] Failed to export JSON result: {e}")


def generate_html_report(output_path, leaderboard, system_info):
    """生成 HTML 效能報表 (benchmark_report.html)。"""
    try:
        cpu_model = system_info["cpu"]
        gpu_model = system_info["gpu"]
        gpu_driver = system_info["gpu_driver"]
        ram_size = system_info["ram"]
        os_info = system_info["os"]

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>FH6 Painter Mark - Benchmark Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 40px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background-color: #1e293b;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            border: 1px solid #334155;
        }}
        h1 {{
            text-align: center;
            color: #38bdf8;
            margin-bottom: 30px;
            border-bottom: 2px solid #38bdf8;
            padding-bottom: 15px;
        }}
        .sys-info {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            background-color: #0f172a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            border: 1px solid #334155;
        }}
        .info-item {{
            font-size: 14px;
        }}
        .info-label {{
            color: #94a3b8;
            font-weight: bold;
        }}
        .info-value {{
            color: #e2e8f0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }}
        th {{
            background-color: #0f172a;
            color: #38bdf8;
        }}
        tr:hover {{
            background-color: #1e293b;
        }}
        .rank-1 {{
            color: #fbbf24;
            font-weight: bold;
        }}
        .rank-2 {{
            color: #cbd5e1;
            font-weight: bold;
        }}
        .rank-3 {{
            color: #b45309;
            font-weight: bold;
        }}
        .score {{
            font-weight: bold;
            color: #38bdf8;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: #64748b;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>FH6 Painter Mark - Performance Report</h1>

        <div class="sys-info">
            <div class="info-item"><span class="info-label">CPU:</span> <span class="info-value">{cpu_model}</span></div>
            <div class="info-item"><span class="info-label">GPU:</span> <span class="info-value">{gpu_model}</span></div>
            <div class="info-item"><span class="info-label">GPU Driver:</span> <span class="info-value">{gpu_driver}</span></div>
            <div class="info-item"><span class="info-label">RAM:</span> <span class="info-value">{ram_size}</span></div>
            <div class="info-item"><span class="info-label">OS:</span> <span class="info-value">{os_info}</span></div>
            <div class="info-item"><span class="info-label">Date:</span> <span class="info-value">{time.strftime("%Y-%m-%d %H:%M:%S")}</span></div>
        </div>

        <h2>Leaderboard</h2>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Engine</th>
                    <th>Tier 1 (Light)</th>
                    <th>Tier 2 (Standard)</th>
                    <th>Tier 3 (Heavy)</th>
                    <th>Weighted Score</th>
                </tr>
            </thead>
            <tbody>
        """
        for rank, entry in enumerate(leaderboard, 1):
            rank_class = f"rank-{rank}" if rank <= 3 else ""
            t1_s = int(entry["tiers"]["Tier_1"]["score"])
            t2_s = int(entry["tiers"]["Tier_2"]["score"])
            t3_s = int(entry["tiers"]["Tier_3"]["score"])
            score_s = int(entry["weighted_score"])

            html_content += f"""
                <tr>
                    <td class="{rank_class}">#{rank}</td>
                    <td>{entry["name"]}</td>
                    <td>{t1_s} pts</td>
                    <td>{t2_s} pts</td>
                    <td>{t3_s} pts</td>
                    <td class="score">{score_s} pts</td>
                </tr>
            """

        html_content += """
            </tbody>
        </table>

        <div class="footer">
            Generated by FH6 Painter Engine Benchmark Suite
        </div>
    </div>
</body>
</html>
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"[Storage] HTML report successfully exported to: {output_path}")
    except Exception as e:
        print(f"[Warning] Failed to export HTML report: {e}")
