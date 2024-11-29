# Browser in Browser

I am surprised that data collection for web agents is still hard. This is a hack done in one day to demonstrate a simple approach to data collection for web agents. 

## Installation

### Frontend

You can use the hosted version at [bib.zhuhao.me](https://bib.zhuhao.me) or you can run your own frontend through

```bash
cd frontend
bun run dev
```

### Backend

Run the backend server. 

```bash
cd backend

# pip install uv # if you don't have uv installed.

uv run playwright install
uv run python main.py
```

## Usage

> [!CAUTION]
> Use `http` only for local development purpose. Please use `https://bib.zhuhao.me` or your self-hosted version together
> with a securly hosted backend (using `https` and `wss` endpoints).

Navigate to [http://bib.zhuhao.me](http://bib.zhuhao.me) and enter the URL you hosted the frontend on.
Put in the backend url (default is `http://localhost:8000`). 

When you input a URL, the backend will open the URL in a browser. 
The screenshot is updated at 33Hz, which can be tuned in the backend.
Now it supports recording the following actions:

- Single click
- Hover
- Scroll
- Type

MIT License @ 2024 Hao Zhu

Cite as
```bibtex
@misc{bib,
  author = {Hao Zhu},
  title = {Browser in Browser data collection toolkit},
  year = {2024},
  howpublished = {\url{https://bib.zhuhao.me}}
}
```