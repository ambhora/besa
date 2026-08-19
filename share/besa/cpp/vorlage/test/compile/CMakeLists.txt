besa_compile_test_add_directory(
  NAME cpp
  PREFIX compile
  LABELS compile production
  TARGET_LIST vorlage::libvorlage
  MODES ci-commit
)
