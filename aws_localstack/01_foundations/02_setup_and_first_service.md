# 01-2 · Setup & your first service

> **Level:** Beginner · **Prerequisites:** [01-1 What is an AWS emulator?](01_what_is_an_aws_emulator.md)
> **Time:** 25 min · **Verified:** 2026-09-01 (Floci latest, Docker 29.7.2)

Get Floci running and create your first AWS resource — an S3 bucket — to prove
the setup before learning the details.

---

## Install the tooling

```bash
pip install awscli-local awscli boto3
```

- **`awscli-local`** (`awslocal`) — the AWS CLI pre-pointed at `localhost:4566`.
- **`awscli`** — the real AWS CLI (`awslocal` wraps it).
- **`boto3`** — the Python AWS SDK.

Docker must be running — Floci *is* a container.

---

## Start Floci

One container, no account, no token:

```bash
docker run -d --name floci -p 4566:4566 floci/floci:latest
```

(Add `-v /var/run/docker.sock:/var/run/docker.sock` when you get to Lambda in
[03-4](../03_core_services/04_lambda_apigateway.md) — Floci runs your functions in
real Docker containers. There's also an optional `floci` CLI — `floci start`,
`floci status`, `floci doctor` — but plain Docker is all you need here.)

Wait for health:

```bash
curl -s http://localhost:4566/_localstack/health
```

Verified response (excerpt):

```json
{"original_edition":"floci-always-free","edition":"community",
 "services":{"s3":"running","dynamodb":"running","sqs":"running", ...}}
```

> Yes, the path says `_localstack` — Floci deliberately serves LocalStack's health
> endpoint (and honours its env vars) so existing tooling works unchanged. The
> backstory is in [05-3](../05_testing_and_ci/03_gotchas_and_pro.md).

---

## Credentials: any value works

Floci ignores credentials but the SDKs still require *some* to be set. Use
dummy values:

```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

---

## Your first resource

Create an S3 bucket and use it — with `awslocal` (note: no `--endpoint-url` needed,
the wrapper adds it):

```bash
awslocal s3 mb s3://my-first-bucket
echo "hello" > hello.txt
awslocal s3 cp hello.txt s3://my-first-bucket/hello.txt
awslocal s3 ls s3://my-first-bucket/
```

Verified (against the capstone's bucket):

```
$ awslocal s3 cp hello.txt s3://linkstash-backups/demo.txt
upload: ./hello.txt to s3://linkstash-backups/demo.txt
$ awslocal s3 ls s3://linkstash-backups/
2026-07-16 15:27:39          6 demo.txt
```

You just created and used real S3 API objects — locally, for free.

---

## Optional: a web UI instead of the CLI

Everything in this course is written with `awslocal`/boto3 because that's what
transfers 1:1 to real AWS — but Floci also has a genuine browser-based console,
**`floci-ui`**, a separate container:

```bash
docker run -d --name floci-ui -p 4500:4500 \
  -e FLOCI_ENDPOINT=http://host.docker.internal:4566 \
  --add-host=host.docker.internal:host-gateway \
  floci/floci-ui:latest
```

Verified 2026-09-01: it serves a real dashboard at `http://localhost:4500` — an
S3 bucket browser, DynamoDB/SQS viewers, Lambda logs, and more, all reading the
Floci instance you already have running. Handy for *poking around* a resource
you just created; every lesson still shows you the CLI/boto3 call, because
that's the skill that's actually portable to a real AWS console or a CI
pipeline.

> **"Floci UI unavailable... could not reach the container runtime"?** Expected
> at this point — the `floci` container you started above doesn't have the
> Docker socket mounted (deliberately; it isn't needed until Lambda in
> [03-4](../03_core_services/04_lambda_apigateway.md)), but the UI checks for it
> regardless of which page you're on. Two options: ignore it if you're only
> browsing S3/DynamoDB, or restart `floci` with the socket mounted now —
> verified this clears the error:
> ```bash
> docker rm -f floci
> docker run -d --name floci -p 4566:4566 \
>   -v /var/run/docker.sock:/var/run/docker.sock -u root floci/floci:latest
> ```

---

## Stop / reset

```bash
docker rm -f floci       # stop and remove (state is gone — it's ephemeral)
```

Ephemeral-by-default is a feature for testing: every run starts clean. Opt-in
persistence exists ([05-3](../05_testing_and_ci/03_gotchas_and_pro.md)).

---

## Recap & next

- ✅ Install `awslocal` + `awscli` + `boto3`; Floci runs as a **Docker container**
  on `:4566` — `docker run -d -p 4566:4566 floci/floci:latest`.
- ✅ Wait for `/_localstack/health` (served for LocalStack compatibility) before
  the first call.
- ✅ Use **dummy credentials** (`test`/`test`); `awslocal` adds the endpoint for you.
  You created and used an S3 bucket.

**Self-check:** Why does `awslocal s3 ls` work without you passing
`--endpoint-url`, while plain `aws s3 ls` would try to reach real AWS?

<details>
<summary>Answer</summary>

`awslocal` is a thin wrapper that **injects `--endpoint-url=http://localhost:4566`**
(and sensible dummy defaults) into every AWS CLI call. Plain `aws` has no endpoint
override, so it uses the default AWS endpoints and talks to real AWS. Same
underlying CLI, different target.

</details>

**→ Next: [01-3 · Endpoints & credentials](03_endpoints_and_credentials.md)**
