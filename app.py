from flask import Flask, request, jsonify
from datetime import datetime
import hashlib

app = Flask(__name__)

# In-memory database
database = {}

# Helper functions
def analyze_string(value):
    value_clean = value.lower()
    length = len(value)
    word_count = len(value.split())
    unique_characters = len(set(value))
    is_palindrome = value_clean == value_clean[::-1]
    sha256_hash = hashlib.sha256(value.encode()).hexdigest()
    
    char_freq = {}
    for char in value:
        char_freq[char] = char_freq.get(char, 0) + 1

    return {
        "length": length,
        "is_palindrome": is_palindrome,
        "unique_characters": unique_characters,
        "word_count": word_count,
        "sha256_hash": sha256_hash,
        "character_frequency_map": char_freq
    }

def parse_natural_language(query):
    filters = {}
    query_lower = query.lower()
    if "palindrome" in query_lower:
        filters["is_palindrome"] = True
    if "single word" in query_lower:
        filters["word_count"] = 1
    if "longer than" in query_lower:
        parts = query_lower.split("longer than")
        try:
            number = int(parts[1].split()[0])
            filters["min_length"] = number + 1
        except:
            pass
    for ch in "abcdefghijklmnopqrstuvwxyz":
        if f"contains {ch}" in query_lower:
            filters["contains_character"] = ch
    return filters

# Routes
@app.route("/strings", methods=["POST"])
def create_string():
    data = request.get_json()
    if not data or "value" not in data:
        return jsonify({"error": "Missing 'value' field"}), 400

    value = data["value"]
    if not isinstance(value, str):
        return jsonify({"error": "'value' must be a string"}), 422

    string_hash = hashlib.sha256(value.encode()).hexdigest()
    if string_hash in database:
        return jsonify({"error": "String already exists"}), 409

    props = analyze_string(value)
    database[string_hash] = {
        "id": string_hash,
        "value": value,
        "properties": props,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    return jsonify(database[string_hash]), 201

@app.route("/strings/<string_value>", methods=["GET"])
def get_string(string_value):
    for item in database.values():
        if item["value"] == string_value:
            return jsonify(item), 200
    return jsonify({"error": "String not found"}), 404

@app.route("/strings", methods=["GET"])
def get_all_strings():
    results = list(database.values())

    # Filters from query params
    args = request.args
    try:
        if "is_palindrome" in args:
            val = args.get("is_palindrome").lower() == "true"
            results = [r for r in results if r["properties"]["is_palindrome"] == val]
        if "min_length" in args:
            min_len = int(args.get("min_length"))
            results = [r for r in results if r["properties"]["length"] >= min_len]
        if "max_length" in args:
            max_len = int(args.get("max_length"))
            results = [r for r in results if r["properties"]["length"] <= max_len]
        if "word_count" in args:
            wc = int(args.get("word_count"))
            results = [r for r in results if r["properties"]["word_count"] == wc]
        if "contains_character" in args:
            ch = args.get("contains_character")
            results = [r for r in results if ch in r["value"]]
    except:
        return jsonify({"error": "Invalid query parameter values or types"}), 400

    filters_applied = {k: args.get(k) for k in args}
    return jsonify({"data": results, "count": len(results), "filters_applied": filters_applied}), 200

@app.route("/strings/filter-by-natural-language", methods=["GET"])
def filter_by_natural_language():
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Missing 'query' parameter"}), 400
    try:
        filters = parse_natural_language(query)
    except:
        return jsonify({"error": "Unable to parse natural language query"}), 400

    results = list(database.values())
    # Apply parsed filters
    try:
        if "is_palindrome" in filters:
            results = [r for r in results if r["properties"]["is_palindrome"] == filters["is_palindrome"]]
        if "word_count" in filters:
            results = [r for r in results if r["properties"]["word_count"] == filters["word_count"]]
        if "min_length" in filters:
            results = [r for r in results if r["properties"]["length"] >= filters["min_length"]]
        if "contains_character" in filters:
            results = [r for r in results if filters["contains_character"] in r["value"]]
        if not results:
            return jsonify({"error": "Query parsed but resulted in conflicting filters"}), 422
    except:
        return jsonify({"error": "Error applying filters"}), 422

    return jsonify({
        "data": results,
        "count": len(results),
        "interpreted_query": {
            "original": query,
            "parsed_filters": filters
        }
    }), 200

@app.route("/strings/<string_value>", methods=["DELETE"])
def delete_string(string_value):
    for key, item in list(database.items()):
        if item["value"] == string_value:
            del database[key]
            return '', 204
    return jsonify({"error": "String not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)