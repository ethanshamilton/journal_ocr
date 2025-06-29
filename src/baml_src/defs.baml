enum Retrievers {
    Vector @description(#"
      Good in any situation. Recommended to use as a default when 
      another retriever type wouldn't be better.
    "#)
    Recent @description(#"
      Gets the most recent articles. Recommended to use when the query has an element of
      recency to it, or when the user is asking for a response that could be confused if
      articles from different times are included.

      Trigger words:
      - Recently
      - Lately
      - Last {week, month, day, etc.}
    "#)
}

function IntentClassifier(query: string) -> Retrievers {
    client "anthropic/claude-3-5-sonnet-20241022"
    prompt #"
        Based on the given query, determine which retriever would be best to answer the query. 

        Return only the name of the retriever, no additional text.

        Query: {{query}}

        {{ctx.output_format}}
    "#
}
