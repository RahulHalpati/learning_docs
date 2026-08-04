# 01-2 · Setup & your first service

> **Level:** Beginner · **Prerequisites:** [01-1 What is LocalStack?](01_what_is_localstack.md)
> **Time:** 25 min · **Verified:** 2026-07-16 (LocalStack 3.8.1, Docker 29.6.1)

Get LocalStack running and create your first AWS resource — an S3 bucket — to prove
the setup before learning the details.

---

## Install the tooling

```bash
pip install localstack awscli-local awscli boto3
```

- **`localstack`** — the CLI that starts/stops the container.
- **`awscli-local`** (`awslocal`) — the AWS CLI pre-pointed at LocalStack.
- **`awscli`** — the real AWS CLI (`awslocal` wraps it).
- **`boto3`** — the Python AWS SDK.

Docker must be running — LocalStack *is* a container.

---

## Start LocalStack (token-free)

Because LocalStack's 2026 CLI requires an account, we run the **pinned community
image directly** with Docker — no signup:

```bash
docker run -d --name localstack_main -p 4566:4566 localstack/localstack:3.8.1
```

Wait for health:

```bash
curl -s http://localhost:4566/_localstack/health
```

Verified response (excerpt):

```json
{"services": {"dynamodb": "available", "s3": "available", "sqs": "available", ...}}
```

```
LocalStack version: 3.8.1
Ready.
```

> Prefer the CLI (`localstack start -d`)? It works too — but the 2026 CLI will ask
> for `LOCALSTACK_AUTH_TOKEN`. The direct `docker run` of `:3.8.1` sidesteps that.
> [04-3](../04_testing_and_ci/03_gotchas_and_pro.md) covers using the latest version.

---

## Credentials: any value works

LocalStack ignores credentials but the SDKs still require *some* to be set. Use
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

## Stop / reset

```bash
docker rm -f localstack_main       # stop and remove (state is gone — it's ephemeral)
```

Ephemeral-by-default is a feature for testing: every run starts clean. Persistence
is a Pro feature ([04-3](../04_testing_and_ci/03_gotchas_and_pro.md)).

---

## Recap & next

- ✅ Install `localstack` + `awslocal` + `awscli` + `boto3`; LocalStack runs as a
  **Docker container** on `:4566`.
- ✅ Run the **pinned `:3.8.1` image** to avoid the 2026 account requirement; check
  `/_localstack/health`.
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
