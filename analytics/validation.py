from monitoring.integrity_score import (
    get_risk_level,
    calculate_integrity_score,
    calculate_face_presence_ratio,
    calculate_event_penalty
)


# ============================================================
# LOW RISK TEST
# ============================================================

def validate_low_risk_level_session():

    browser_events = [
        {"event_type": "tab_switch"},
        {"event_type": "focus_lost"},
    ]

    face_presence_ratio = 98

    # Calculate event penalty
    penalty = calculate_event_penalty(browser_events)

    # Calculate final integrity score
    score = calculate_integrity_score(
        browser_events,
        face_presence_ratio
    )

    # Determine risk from final score
    risk = get_risk_level(score)

    print("\n========== LOW RISK TEST ==========")
    print(f"Face Presence Ratio : {face_presence_ratio}")
    print(f"Event Penalty       : {penalty}")
    print(f"Integrity Score     : {score}")
    print(f"Risk Level          : {risk}")
    print("Expected Risk Level : Low")


# ============================================================
# MEDIUM RISK TEST
# ============================================================

def validate_medium_risk_level_session():

    browser_events = [
        {"event_type": "tab_switch"},
        {"event_type": "tab_switch"},
        {"event_type": "focus_lost"},
        {"event_type": "right_click"},
    ]

    face_presence_ratio = 98

    # Calculate event penalty
    penalty = calculate_event_penalty(browser_events)

    # Calculate final integrity score
    score = calculate_integrity_score(
        browser_events,
        face_presence_ratio
    )

    # Determine risk from final score
    risk = get_risk_level(score)

    print("\n========== MEDIUM RISK TEST ==========")
    print(f"Face Presence Ratio : {face_presence_ratio}")
    print(f"Event Penalty       : {penalty}")
    print(f"Integrity Score     : {score}")
    print(f"Risk Level          : {risk}")
    print("Expected Risk Level : Medium")


# ============================================================
# HIGH RISK TEST
# ============================================================

def validate_high_risk_level_session():

    browser_events = [
        {"event_type": "tab_switch"},
        {"event_type": "tab_switch"},
        {"event_type": "tab_switch"},
        {"event_type": "tab_switch"},
        {"event_type": "tab_switch"},

        {"event_type": "focus_lost"},
        {"event_type": "focus_lost"},
        {"event_type": "focus_lost"},

        {"event_type": "copy_attempt"},
        {"event_type": "paste_attempt"},

        {"event_type": "right_click"},
    ]

    face_presence_ratio = 98

    # Calculate event penalty
    penalty = calculate_event_penalty(browser_events)

    # Calculate final integrity score
    score = calculate_integrity_score(
        browser_events,
        face_presence_ratio
    )

    # Determine risk from final score
    risk = get_risk_level(score)

    print("\n========== HIGH RISK TEST ==========")
    print(f"Face Presence Ratio : {face_presence_ratio}")
    print(f"Event Penalty       : {penalty}")
    print(f"Integrity Score     : {score}")
    print(f"Risk Level          : {risk}")
    print("Expected Risk Level : High")


# ============================================================
# MAIN
# ============================================================

def main():

    validate_low_risk_level_session()

    validate_medium_risk_level_session()

    validate_high_risk_level_session()


if __name__ == "__main__":
    main()