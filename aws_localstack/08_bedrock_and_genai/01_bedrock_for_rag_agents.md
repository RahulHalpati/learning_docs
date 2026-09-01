# 08-1 · Bedrock for RAG & agents

> **Level:** Intermediate · **Prerequisites:** [02 · IAM & access](../02_iam_and_access/01_access_model_iam_sts.md), [langchain_rag 01-3](../../langchain_rag/01_foundations/03_your_first_chat_model.md)
> **Time:** 30 min · **Verified:** 2026-09-01 (IAM policy shape, `langchain-aws` import) — **Needs:** a real AWS account for the model calls themselves; no Floci equivalent (see the caveat below).

## Why this module exists

Every other lesson in this course is storage, messaging, or compute — plumbing
that's identical whether an LLM is involved or not. **Bedrock** is AWS's answer to
"how do I call an LLM from inside my AWS account instead of a third party's API":
one boto3 client, IAM-authenticated, billed like every other AWS service, serving
models from Anthropic, Meta, Mistral, and Amazon's own Nova/Titan line. It's the
bridge between this course and the [LangChain/RAG](../../langchain_rag/) and
[LangGraph](../../langgraph/) courses — same RAG chains and agent graphs, Bedrock
is just another model provider underneath.

## Why an enterprise picks Bedrock over calling OpenAI/Anthropic directly

Not technology — **trust boundary**. The model call never leaves your AWS
account: it's authenticated with **IAM** (not a bearer API key floating around
in an env var), it can run inside a **VPC endpoint** so traffic never touches the
public internet, and it shows up in **CloudWatch/CloudTrail** like everything
else you've provisioned. For a bank, hospital, or GCC already on AWS, that's the
difference between "ships in a sprint" and "six months of security review" —
which is exactly why Bedrock shows up so often in Indian enterprise/GCC job
postings.

## Step 1 — enable model access (one-time, console)

Unlike every other Bedrock API, this step has no boto3 equivalent: in the
**Bedrock console → Model access**, request access to the models you want
(Anthropic Claude, Amazon Nova, etc.). It's instant for AWS's own models, near-
instant for most third-party ones. Do this before writing any code — an
`AccessDeniedException` on your first `InvokeModel` call almost always means
this step, not IAM.

## Step 2 — the IAM permissions (this is the part that transfers)

Bedrock is authorized like every other AWS service — a policy your role needs,
same shape as [02-2](../02_iam_and_access/02_roles_and_policies_per_service.md):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
    "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude*"
  }]
}
```

Scope `Resource` to the specific model family you use — least privilege, same
lesson as everywhere else in this course. Bedrock **Agents**/**Knowledge Bases**
(step 5) need additional actions (`bedrock:Retrieve`, `bedrock:InvokeAgent`, …) on
top of this.

## Step 3 — call it with boto3 (the `converse` API)

`converse` is the modern, provider-agnostic call — same request/response shape
whether the model is Claude, Nova, or Llama:

```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="anthropic.claude-haiku-4-5",   # check the current ID in the Bedrock console
    messages=[{"role": "user", "content": [{"text": "In one sentence, what is RAG?"}]}],
    inferenceConfig={"maxTokens": 200, "temperature": 0},
)
print(response["output"]["message"]["content"][0]["text"])
```

That's the whole mechanical difference from calling Anthropic/OpenAI directly:
`boto3.client("bedrock-runtime")` instead of a provider SDK, IAM instead of an
API key. (The older per-model `invoke_model` API still exists — you hand-build
each provider's own request body — but `converse` is what you should reach for
now.)

## Step 4 — call it from LangChain (the part that plugs into your other courses)

`langchain-aws` gives you `ChatBedrockConverse` — a drop-in for every
`ChatOpenAI`/`ChatOllama`/`ChatNVIDIA` line in the [langchain_rag environment
setup](../../langchain_rag/01_foundations/02_environment_setup.md):

```bash
uv pip install langchain-aws
```

```python
from langchain_aws import ChatBedrockConverse

llm = ChatBedrockConverse(model="anthropic.claude-haiku-4-5", region_name="us-east-1", temperature=0)
print(llm.invoke("In one sentence, what is RAG?").content)
```

Same `.invoke()`, same `|` chains, same LangGraph nodes you've already built —
swap this line into `03_rag_fundamentals/04_build_a_rag_chain.md`'s RAG chain or
any `get_model()` helper from the LangGraph course and nothing else changes.
`BedrockEmbeddings` (same package) does the same for the embedding side of RAG.

## Step 5 — managed RAG/agents, or build your own?

Bedrock also offers **Knowledge Bases** (AWS runs chunk → embed → store →
retrieve for you) and **Agents** (AWS runs the tool-calling loop). This is the
real either/or decision — not "Bedrock vs. LangChain", which was never a choice
(§ above shows they compose):

| | Bedrock Knowledge Bases / Agents | Your own (LangChain/LangGraph) |
|---|---|---|
| Setup | Console/CLI config, no RAG code | You write the chain/graph |
| Control | Fixed chunking/retrieval strategy | Every step is yours — reranking, hybrid search, custom loops, self-correction ([langgraph 08-2](../../langgraph/08_real_world/02_self_correcting_rag.md)) |
| Portability | AWS-locked | Runs anywhere; swap providers freely |
| Debuggability | Black box when it retrieves wrong | You can inspect/fix every step |
| Best for | Ship fast, standard RAG, team is AWS-only | Custom retrieval logic, multi-cloud, anything this course's RAG/agent sections cover |

**Rule of thumb:** reach for Knowledge Bases/Agents when the requirement is "add
RAG to this AWS app quickly" and the default behavior is good enough. Reach for
your own stack — everything in `langchain_rag`/`langgraph` — the moment you need
control: a custom reranker, a self-correction loop, multi-agent orchestration, or
just the freedom to run the same code against Ollama in dev and Bedrock in prod.

## ⚠️ The Floci/LocalStack caveat

Floci lists `bedrock-runtime` as a running service, but — verified by reading its
own docs — it's an **in-process stub**: canned `Converse`/`InvokeModel` responses,
no real inference, no Ollama backing like you might expect. So the code above is
correct and will run against Floci without erroring, but the reply is fake. There
is no substitute for testing against real Bedrock here — budget cents, not
dollars, for it (Claude Haiku– and Nova Lite–class models cost fractions of a
cent per call).

## Recap & next

- ✅ Bedrock = AWS's managed model-hosting service: IAM-authenticated,
  VPC-reachable, billed like any AWS service — that account boundary is *why*
  enterprises pick it, not raw model quality.
- ✅ Model access is enabled once in the console; calls go through
  `boto3.client("bedrock-runtime").converse(...)` or, from LangChain,
  `ChatBedrockConverse` — a one-line swap for any chat model in your other
  courses.
- ✅ Knowledge Bases/Agents are the **managed, low-control** path to RAG/agents;
  your own LangChain/LangGraph stack is the **flexible, portable** path. They're
  not mutually exclusive with using Bedrock as the model.
- ✅ Floci's Bedrock is a stub — this module's code is real, but verifying it
  needs a real (cheap) AWS account.

## Exercise

Take the RAG chain you built in [langchain_rag 03-4](../../langchain_rag/03_rag_fundamentals/04_build_a_rag_chain.md)
and swap only the `llm` line for `ChatBedrockConverse`. What IAM permission does
your AWS credential need for the chain to run, and where would you attach it if
this were deployed as a Lambda function ([03-4](../03_core_services/04_lambda_apigateway.md))?

<details>
<summary>Answer</summary>

`bedrock:InvokeModel` (and `InvokeModelWithResponseStream` if you stream) scoped
to the model you're calling. In a Lambda deployment it goes on the **Lambda
execution role** — the same role that already needs `dynamodb:*`/`s3:*`
permissions for the rest of the app, per [02-2](../02_iam_and_access/02_roles_and_policies_per_service.md)'s
least-privilege pattern. Nothing about *where* the code runs changes which
permission it needs — that's the point of IAM being the same model everywhere.

</details>

→ Course finishes here. Back to **[README](../README.md)** or the
**[99 · Capstone](../99_project_linkstash_cloud/README.md)**.
