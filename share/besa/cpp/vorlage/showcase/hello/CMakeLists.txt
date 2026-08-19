add_custom_target(
  showcase.hello
  COMMAND $<TARGET_FILE:vorlage>
  DEPENDS vorlage
  VERBATIM
)
