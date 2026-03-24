import json
import os

from soupsieve.css_match import Inputs


class Inference():
    def __init__(self):
        trend_values = {
            "strong_decrease":-2,
            "decrease":-1,
            "neutral":0,
            "increase":1,
            "strong_increase":2,
        }

        self.RULES = [
            {
                "name": "R1",
                "if": [("cpi", "critical"), ("funds_rate", "low")],
                "op": "AND",
                "value": trend_values["strong_increase"],
            },
            {
                "name":"R2",
                "if": [("cpi", "low"), ("dolar_index", "high")],
                "op": "AND",
                "value": trend_values["decrease"],
            },
            {
                "name":"R3",
                "if": [("funds_rate", "high")],
                "op": "AND",
                "value": trend_values["decrease"],
            },
            {
                "name":"R4",
                "if": [("dolar_index", "low")],
                "op": "AND",
                "value": trend_values["increase"],
            },
            {
                "name":"R5",
                "if": [("geopolitical_sentiment", "high")],
                "op": "AND",
                "value": trend_values["strong_increase"],
            },
            {
                "name":"R6",
                "if": [("vix_index", "high")],
                "op":"AND",
                "value": trend_values["increase"],
            },
            {
                "name":"R7",
                "if": [("geopolitical_sentiment", "medium"),("vix_index","medium")],
                "op":"AND",
                "value": trend_values["increase"],
            },
            {
                "name":"R8",
                "if": [("banks_demand", "critical")],
                "op":"AND",
                "value":    trend_values["increase"],

            }
        ]

    def left_shoulder(self, x, a, b):
        if x <= a:
            return 1.0
        if x >= b:
            return 0.0
        return (b - x) / (b - a)


    def triangle(self, x, a, b, c):
        if x <= a or x >= c:
            return 0.0
        if x <= b:
            return (x - a) / (b - a)
        return (c - x) / (c - b)


    def right_shoulder(self, x, a, b):
        if x <= a:
            return 0.0
        if x >= b:
            return 1.0
        return (x - a) / (b - a)


    def fuzzify_cpi(self, x):
        return {
            "very_low": self.left_shoulder(x, 240, 270),
            "low": self.triangle(x, 240, 270, 300),
            "medium": self.triangle(x, 270, 300, 320),
            "high": self.triangle(x, 300, 320, 340),
            "critical": self.right_shoulder(x, 320, 340)
        }


    def fuzzify_fed_funds(self, x):
        return {
            "very_low": self.left_shoulder(x, 1.0, 2.5),
            "low": self.triangle(x, 1.0, 2.5, 4.0),
            "medium": self.triangle(x, 2.5, 4.0, 5.5),
            "high": self.triangle(x, 4.0, 5.5, 6.5),
            "critical": self.right_shoulder(x, 5.5, 7.0)
        }


    def fuzzify_dollar_index(self,x):
        return {
            "low": self.left_shoulder(x, 94, 106),
            "medium": self.triangle(x, 94, 106, 120),
            "high": self.right_shoulder(x, 104, 120),
        }


    def fuzzify_geopolitical_tensions(self, x):
        return {
            "low": self.left_shoulder(x, 100, 250),
            "medium": self.triangle(x, 100, 175, 250),
            "high": self.right_shoulder(x, 250, 400),
        }


    def fuzzify_market_sentiment(self, x):
        return {
            "low": self.left_shoulder(x, 16, 32),
            "medium": self.triangle(x, 16, 24, 32),
            "high": self.right_shoulder(x, 28, 85),
           }


    def fuzzify_central_bank_demand(self, x):
        return {
            "very_low": self.left_shoulder(x, 50, 120),
            "low": self.triangle(x, 40, 120, 200),
            "medium": self.triangle(x, 100, 200, 260),
            "high": self.triangle(x, 180, 240, 260),
            "critical": self.right_shoulder(x, 240, 260),
        }


    def read_json_values(self):
        folder_path = "knowledge_base/"
        data = []
        json_files_list = sorted(os.listdir(folder_path))
        for file_name in json_files_list:
            if file_name.startswith("kb_gold_2025") and file_name.endswith(".json"):
                file_path = os.path.join(folder_path, file_name)
                with open(file_path, 'r') as f:
                    d = json.load(f)
                    data.append({"date": d["analyzed_date"],
                                 "values": d["variables_fuzzy"],
                                })
        return data


    def fuzzify_all(self, data):
        fuzzified_data = []

        for item in data:
            d = item["values"]

            fuzzified_data.append({
                "date": item["date"],
                "cpi": self.fuzzify_cpi(d["inflation_cpi"]),
                "funds_rate": self.fuzzify_fed_funds(d["fed_funds_rate"]),
                "dolar_index": self.fuzzify_dollar_index(d["dolar_index"]),
                "geopolitical_sentiment": self.fuzzify_geopolitical_tensions(d["geopolitical_sentiment"]),
                "vix_index": self.fuzzify_market_sentiment(d["vix_index"]),
                "banks_demand": self.fuzzify_central_bank_demand(d["banks_demand"]),
            })

        return fuzzified_data

    def evaluate_rule(self, fuzzy_day, rule):
        values = []

        for variable, label in rule["if"]:
            values.append(fuzzy_day[variable][label])

        if rule["op"] == "AND":
            mu = min(values)
        elif rule["op"] == "OR":
            mu = max(values)
        else:
            raise ValueError("Unknown rule {}".format(rule["op"]))

        return mu, rule["value"], rule["name"]


    def apply_rules(self, fuzzy_day):
        results = []
        for rule in self.RULES:
            result = self.evaluate_rule(fuzzy_day, rule)
            if result[0] > 0:
                results.append(result)
        return results


    def defuzzify(self, rule_results):
        numerator = sum(mu * value for mu, value, _ in rule_results)
        denominator = sum(mu for mu, _, _ in rule_results)

        if denominator == 0:
            return 0.0

        return numerator / denominator


    def interpret_trend(self, score):
        if score <= -1.5:
            return "Scădere Puternică"
        elif score < -0.3:
            return "Scădere"
        elif score <= 0.3:
            return "Neutru"
        elif score < 1.5:
            return "Creștere"
        else:
            return "Creștere Puternică"


    def infer_for_day(self, fuzzy_day):
        rule_results = self.apply_rules(fuzzy_day)
        score = self.defuzzify(rule_results)
        trend = self.interpret_trend(score)

        return {
            "date": fuzzy_day["date"],
            "score": round(score, 4),
            "trend": trend,
            "rules": rule_results
        }

    def infer_for_date(self, target_date, fuzzified_data):
        for fuzzy_day in fuzzified_data:
            if fuzzy_day["date"] == target_date:
                return self.infer_for_day(fuzzy_day)
        return None


if __name__ == "__main__":
    data = {
        "analyzed_date": "2026-03-24",
        "generated_at": "2026-03-24 21:26:06",
        "variables_fuzzy": {
            "inflation_cpi": 326.785,
            "fed_funds_rate": 3.1,
            "dolar_index": 99.235,
            "geopolitical_sentiment": 335.15,
            "vix_index": 25.88,
            "banks_demand": 230.2
        }
    }

    item = {
        "date": data["analyzed_date"],
        "values": data["variables_fuzzy"]
    }
    inference = Inference()
    fuzzified_data = inference.fuzzify_all([item])
    result = inference.infer_for_date("2026-03-24", fuzzified_data)

    if result:
        print("Data:", result["date"])
        print("Scor:", result["score"])
        print("Trend:", result["trend"])
        print("Reguli activate:")
        for mu, value, name in result["rules"]:
            print(f"{name}: mu={mu:.4f}, value={value}")
    else:
        print("Data nu a fost găsită.")