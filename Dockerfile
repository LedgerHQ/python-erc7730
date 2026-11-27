ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION:?}-slim AS builder

WORKDIR /build
ARG PDM_VERSION
RUN pip install --no-cache-dir "pdm==${PDM_VERSION:?}"
COPY pyproject.toml pdm.lock ./
RUN pdm export --prod --output requirements.txt \
    && python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir --require-hashes --requirement requirements.txt

COPY README.md LICENSE ./
COPY src src
ARG VERSION
RUN PDM_PEP517_SCM_VERSION="${VERSION:?}" /venv/bin/pip install --no-cache-dir --no-deps .

FROM python:${PYTHON_VERSION:?}-slim

LABEL org.opencontainers.image.source=https://github.com/LedgerHQ/python-erc7730
COPY --from=builder /venv /venv
ENV PATH=/venv/bin:$PATH
USER 65532:65532
EXPOSE 8730
ENTRYPOINT ["erc7730"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8730"]
