def match(name, companies, min_threshold):
    """
    :param name: name provided in the user uploaded record.
    :param companies: List of company dictionaries to match to. For simplicity you can pass the full
        list of companies provided.
    :param min_threshold: minimum score for acceptable match, 0 <= min_threshold <= 1

    :return: dictionary with the best match, fields are `match_name`, `match_id` and `score`.
    """
    best_match = None
    best_score = 0
    for company in companies:
        # Unify casing for both names
        name_upper = name.upper()
        company_name_upper = company['name'].upper()

        # Extract tokens (words) from names
        record_name_tokens = set(name_upper.split())
        company_name_tokens = set(company_name_upper.split())

        # measure name similarity using Jaccard coefficient measured as
        # J(A, B) = |A intersect B| / |A union B|
        score = (
            len(record_name_tokens.intersection(company_name_tokens)) /
            float(len(record_name_tokens.union(company_name_tokens)))
        )

        if score > best_score and score >= min_threshold:
            best_score = score
            best_match = company

    if best_match:
        return {'match_name': best_match['name'], 'match_id': best_match['id'], 'match_score': best_score}
    else:
        return {'match_name': None, 'match_id': None, 'match_score': None}
