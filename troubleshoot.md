# Troubleshooting

## The Kaggle notebook is stuck and `dami kaggle start` will not start it

### Symptoms

- `dami kaggle start` does not reach "brain is ready". The notebook stays `QUEUED`, or a new push fails.
- `kaggle kernels status <your-username>/llm-dami` shows `KernelWorkerStatus.QUEUED` for a long time.
- A push fails with:

  ```
  ❌ kaggle kernels push failed (HTTP None).
  Kaggle says: Maximum batch GPU session count of 2 reached.
  ```

### Cause

Sometimes Kaggle notebooks just get stuck. This is a problem on Kaggle's side, not something you did wrong.

Kaggle lets an account run at most **2 GPU sessions at the same time**. A stuck run of your notebook
(queued or running) still holds one of those slots, even after you've given up on it. Every new push, even
to a different notebook, is refused until a slot is free.

The Kaggle command-line tool cannot stop a running notebook. You have to stop it on kaggle.com.

### Solution

1. **Free the GPU slots.** On kaggle.com, open **Your Work → Code**, or check the "Active sessions" panel on
   the right of any notebook editor. Stop every running or queued session of `llm-dami`, and close any open
   editor tab for it.

2. **Switch to a copy of the notebook with a different name.** If the old notebook still won't start, give
   up on it. In `.env`, change:

   ```
   KAGGLE_NOTEBOOK=<your-username>/llm-dami
   ```

   to a new name, for example:

   ```
   KAGGLE_NOTEBOOK=<your-username>/llm-dami-2
   ```

   You don't need to create the notebook on kaggle.com first. If no notebook with that name exists,
   `dami kaggle start` creates it as a **private** notebook from the notebook in this repository
   (`src/dami/kaggle/llm_DaMi.ipynb`).

3. **Start it again:**

   ```bash
   dami kaggle start
   ```

   Check that it works with `dami kaggle status`.

### If you work with a partner

Your partner reads your notebook's log through `PARTNER_NOTEBOOK` in their `.env`. After you switch notebooks:

- Share the **new** notebook with them on kaggle.com (Share → add them as a collaborator).
- They change their `.env` to `PARTNER_NOTEBOOK=<your-username>/llm-dami-2`, then run `dami kaggle partner`.

## Grafana or Langfuse do not accept the printed credentials

### Symptoms

- `dami obs up` prints the logins, but Grafana (http://127.0.0.1:3001) or Langfuse (http://127.0.0.1:3000)
  says the user name or password is wrong.
- Langfuse does not open at all: its container keeps restarting.

### Cause

Grafana and Langfuse store their passwords in Docker volumes the **first** time they start, and keep them
after that. If the passwords in your `.env` were created again later (for example after you copied
`.env.example` over your `.env`), the stored ones no longer match the printed ones.

### Solution

Delete the stored data and start again. This deletes all metrics and traces recorded so far.

```bash
dami obs delete          # answer y to confirm
dami obs up --traces
```

Log in with the credentials that `dami obs up` prints now. Langfuse needs about 1-2 minutes for its first start.

If Grafana says the login is "temporarily blocked", you tried too many wrong passwords: wait 5 minutes.
