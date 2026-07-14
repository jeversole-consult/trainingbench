# Power Search and Compare

These two tabs are for questions where you want more than one
opinion — either from multiple external AI services or from
two different database/model configurations side by side.

## Power Search

The **Power Search** tab sends the same question to multiple
external AI services (for example, Gemini, ChatGPT, Grok) and
shows their answers together. This is useful when:

- You want to sanity-check an answer against multiple models.
- The question is broad enough that different models are
  likely to emphasise different things.
- You are researching a topic and want a quick survey of what
  different services say.

### How to use it

1. Type your question in the input box.
2. Select which AI services to consult. The available services
   depend on which API keys are configured on your instance.
3. Click **Run Power Search**.
4. Answers from each selected service appear side by side.

The services are queried in parallel, so total wait time is
approximately the slowest single service, not the sum of all.

### Notes

- Power Search consults external services. Your question and
  their responses go over the network to those services.
  Consider whether the question contains anything you would
  not want to send to a third party.
- Not every service will always respond. If one is down or
  rate-limited, the others still return.

## Compare

The **Compare** tab is different in kind: it runs the same
question against **two internal configurations** and shows the
answers side by side. The two sides can differ by:

- Which database is used.
- Which model or model configuration answers.

This is useful when:

- You want to see how the same question is answered against
  two different knowledge bases (e.g. "old policy" vs "new
  policy" databases).
- You are evaluating whether a change to the model or database
  produces meaningfully different answers.

### How to use it

1. Enter your research question.
2. Configure the left-side and right-side runs — pick database
   and model for each.
3. Run the comparison. Both answers come back and appear
   alongside each other.
4. Read them together. Where the answers agree, you have
   higher confidence; where they diverge, you have something
   to investigate.

### Notes

- Compare is internal — it doesn't consult any external AI
  service. Your question stays on the instance.
- Compare pays the cost of both runs. It is slower than a
  single Ask Questions call, roughly the sum of the two runs.
