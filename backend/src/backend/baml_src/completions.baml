enum SearchOptions {
  VECTOR
  RECENT
  NONE
}

function IntentClassifier(query: string) -> SearchOptions {
  client "openai/gpt-5-mini"
  prompt #"
    <INSTRUCTIONS>
    Determine which search method will be best for the following query:
    </INSTRUCTIONS>
    <QUERY>
    {{query}}
    </QUERY>
    <OUTPUT_FORMAT>
    {{ctx.output_format}}
    </OUTPUT_FORMAT>
  "#
}
