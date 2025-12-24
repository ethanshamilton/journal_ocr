
// INTENT CLASSIFICATION

enum SearchOptions {
  VECTOR
  RECENT
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

// DIRECT CHAT

function DirectChat(messages: string, entries: string) -> string {
    client "openai/gpt-5"
    prompt #"
        <INSTRUCTIONS>
        Provide an empathetic and analytical response to the user.
        </INSTRUCTIONS>
        <RELEVANT_ENTRIES>
        {{entries}}
        </RELEVANT_ENTRIES>
        <CHAT_HISTORY>
        {{messages}}
        </CHAT_HISTORY>
        <OUTPUT_FORMAT>
        {{ctx.output_format}}
        </OUTPUT_FORMAT>
    "#
}
