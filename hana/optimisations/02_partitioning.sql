-- ===========================================================================
-- Optimisation 2: range partitioning on fiscal year, for partition pruning
--
-- Almost every query this cockpit issues is bounded by fiscal year - a close
-- monitor looks at the current year, a variance analysis at one year against
-- the last. Unpartitioned, "WHERE fiscal_year = 2026" still touches all four
-- years of data and discards three of them.
--
-- Range partitioning by fiscal year lets the optimiser skip the partitions a
-- filter excludes: the work not done is the whole point, and it is also what
-- makes this an eco-design measure and not only a speed one. Data not scanned
-- is memory not touched and CPU not spent, on every execution, forever.
--
-- FACT_JOURNAL needs two levels. Its primary key is journal_id, and HANA will
-- not range-partition on a column outside a unique constraint - so level 1 is
-- a hash on the key (satisfying the constraint) and level 2 is the range that
-- actually prunes. This is the standard pattern and the reason a single-level
-- range partition on a keyed table fails.
--
-- The aggregate has no primary key, so a single-level range partition is
-- enough there.
-- ===========================================================================

ALTER TABLE "NOVASPACE_RAW"."FACT_JOURNAL"
  PARTITION BY
    HASH ("journal_id") PARTITIONS 4,
    RANGE ("fiscal_year") (
      PARTITION 2023 <= VALUES < 2024,
      PARTITION 2024 <= VALUES < 2025,
      PARTITION 2025 <= VALUES < 2026,
      PARTITION 2026 <= VALUES < 2027,
      PARTITION OTHERS
    );

-- The OTHERS partition is not optional. Without it a posting in a fiscal year
-- nobody planned for is rejected at insert time, and the loader fails on the
-- first day of the next year for a reason that looks nothing like the cause.
ALTER TABLE "NOVASPACE_L3"."AGG_JOURNAL_MONTHLY"
  PARTITION BY
    RANGE ("fiscal_year") (
      PARTITION 2023 <= VALUES < 2024,
      PARTITION 2024 <= VALUES < 2025,
      PARTITION 2025 <= VALUES < 2026,
      PARTITION 2026 <= VALUES < 2027,
      PARTITION OTHERS
    );
