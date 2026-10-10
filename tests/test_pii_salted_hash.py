import hashlib
from src.agents.profiler import ProfilerAgent
from src.agents.translator import TranslatorAgent


def test_pii_salted_hash_generation(temp_legacy_db, temp_target_db):
    s_runner, s_path, ddl_map = temp_legacy_db
    t_runner, t_path = temp_target_db

    profiler = ProfilerAgent(legacy_db=s_runner)
    cust_profiles = profiler.profile_columns("raw_customers", ddl_map["raw_customers"])

    salt1 = "test_salt_alpha"
    salt2 = "test_salt_beta"

    t1 = TranslatorAgent(target_db=t_runner, source_db=s_runner, pii_salt=salt1)
    stg1 = t1.execute_target_duckdb("raw_customers", ddl_map["raw_customers"], columns=cust_profiles)
    rows1 = t_runner.fetch_all(f"SELECT CUST_NAT_DOC_NUM_ID FROM {stg1} WHERE CUST_LST_ADDR_ID_TX = 'c_101'")
    hash1 = rows1[0]["CUST_NAT_DOC_NUM_ID"]

    # Verify not plain SHA-256 (rainbow table defense)
    plain_hash = hashlib.sha256("123.456.789-00".encode("utf-8")).hexdigest()
    assert hash1 != plain_hash, "Hash must be salted, not plain SHA-256"

    # Verify expected salted hash
    expected_hash = hashlib.sha256(f"123.456.789-00{salt1}".encode("utf-8")).hexdigest()
    assert hash1 == expected_hash

    # Verify changing salt changes hash output
    t2 = TranslatorAgent(target_db=t_runner, source_db=s_runner, pii_salt=salt2)
    stg2 = t2.execute_target_duckdb("raw_customers", ddl_map["raw_customers"], columns=cust_profiles)
    rows2 = t_runner.fetch_all(f"SELECT CUST_NAT_DOC_NUM_ID FROM {stg2} WHERE CUST_LST_ADDR_ID_TX = 'c_101'")
    hash2 = rows2[0]["CUST_NAT_DOC_NUM_ID"]

    assert hash1 != hash2, "Different salts must produce distinct hashes"
