
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

// PROMPT GENERATOR

enum AnalysisStep {
  SUBYEAR
  YEAR
  FINAL
}

function PromptGenerator(query: string, step: AnalysisStep) -> string {
    client "openai/gpt-4o-mini"
    prompt #"
        Generate a medium length prompt for an analyst language model that will guide the analyst to
        most effectively process the given data. Here is an example of a prompt that was used before:

        <EXAMPLE>
        Please analyze all the journal entries shown to provide a comprehensive analysis of how they pertain to the query.
        This message will be used to provide compressed context about the year you are analyzing to a further LLM call that
        is responsible for synthesizing an overall answer to the user's query.
        </EXAMPLE>

        DO NOT PROVIDE A STRUCTURED OUTPUT SCHEMA. This will be handled elsewhere.

        The goal is to dynamically tune the analyst model to attend to the action the user is requesting.

        There are three types of analyst model: subyear, year, and final analysis models. Year models provide intermediate reports
        which will be processed by the final analysis model. Subyear models are used in cases where a full yearly analysis is too
        large for a model's context window. The result of the final analysis model will be shown to the
        user. Be sure to convey any relevant information about the step in the process to the analyst model so it is able
        to effectively provide information to the consuming entity.

        USER QUERY: {{query}}

        STEP: {{step}}

        {{ctx.output_format}}
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
