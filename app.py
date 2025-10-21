from flask import Flask, request, jsonify
from datetime import datetime
import hashlib

app = Flask(__name__)

# In-memory database
database = {}

# Helper function to analyze string
def analyze_string(value):
    return {
        "length": len(value),
        "is_uppercase": value.isupper(),
        "is_lowercase": value.islower(),
        "has_numbers": any(ch.isdigit() for ch in value),
        "has_special_chars": any(not ch.isalnum() for ch in value),
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

# Create a new string
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

# Get a specific string
@app.route("/strings/<string_value>", methods=["GET"])
def get_string(string_value):
    for item in database.values():
        if item["value"] == string_value:
            return jsonify(item), 200
    return jsonify({"error": "String not found"}), 404

# Get all strings
@app.route("/strings", methods=["GET"])
def get_all_strings():
    results = list(database.values())
        # Retrieve query parameters
    is_palindrome = request.args.get("is_palindrome")
    min_length = request.args.get("min_length", type=int)
    max_length = request.args.get("max_length", type=int)
    word_count = request.args.get("word_count", type=int)
    contains_character = request.args.get("contains_character")

    # Apply filters
    if is_palindrome is not None:
        if is_palindrome.lower() not in ["true", "false"]:
            return jsonify({"error": "Invalid value for is_palindrome"}), 400
        results = [r for r in results if r["properties"]["is_palindrome"] == (is_palindrome.lower() == "true")]

    if min_length is not None:
        results = [r for r in results if r["properties"]["length"] >= min_length]

    if max_length is not None:
        results = [r for r in results if r["properties"]["length"] <= max_length]

    if word_count is not None:
        results = [r for r in results if r["properties"]["word_count"] == word_count]

    if contains_character:
        if len(contains_character) != 1:
            return jsonify({"error": "contains_character must be a single character"}), 400
        results = [r for r in results if contains_character in r["value"]]

    # Build response
    response = {
        "data": results,
        "count": len(results),
        "filters_applied": {
            "is_palindrome": is_palindrome,
            "min_length": min_length,
            "max_length": max_length,
            "word_count": word_count,
            "contains_character": contains_character
        }
    }
    return jsonify(response), 200

    return jsonify(results), 200

@app.route("/strings/<string_value>", methods=["DELETE"])
def delete_string(string_value):
    for key, item in list(database.items()):
        if item["value"] == string_value:
            del database[key]
            return '', 204  # No Content
    return jsonify({"error": "String not found"}), 404

@app.route("/strings/filter-by-natural-language", methods=["GET"])
def filter_by_natural_language():
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Missing 'query' parameter"}), 400

    query_lower = query.lower()
    filters = {}

    # Simple parsing logic (you can expand this later)
    if "palindromic" in query_lower or "palindrome" in query_lower:
        filters["is_palindrome"] = True
    if "single word" in query_lower:
        filters["word_count"] = 1
    if "longer than" in query_lower:
        words = query_lower.split()
        for i, word in enumerate(words):
            if word == "than" and i + 1 < len(words):
                try:
                    filters["min_length"] = int(words[i + 1]) + 1
                except ValueError:
                    pass
    if "containing the letter" in query_lower or "contains the letter" in query_lower:
        parts = query_lower.split("letter")
        if len(parts) > 1:
            letter = parts[1].strip().split()[0]
            filters["contains_character"] = letter

    # Apply filters (reuse logic from earlier endpoint)
    results = list(database.values())
    if "is_palindrome" in filters:
        results = [r for r in results if r["properties"]["is_palindrome"] == filters["is_palindrome"]]
    if "word_count" in filters:
        results = [r for r in results if r["properties"]["word_count"] == filters["word_count"]]
    if "min_length" in filters:
        results = [r for r in results if r["properties"]["length"] >= filters["min_length"]]
    if "contains_character" in filters:
        results = [r for r in results if filters["contains_character"] in r["value"]]

    if not results:
        return jsonify({"error": "No matching strings found"}), 404

    return jsonify({
        "data": results,
        "count": len(results),
        "interpreted_query": {
            "original": query,
            "parsed_filters": filters
        }
    }), 200




if __name__ == "__main__":
    app.run(debug=True)
