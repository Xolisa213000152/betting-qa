[pytest]
testpaths = tests

markers =
    ui:    End-to-end UI tests (require Chrome + ChromeDriver)
    api:   API-only tests (no browser needed)
    smoke: Critical happy-path subset

addopts =
    -v
    --tb=short
    --html=reports/test_report.html
    --self-contained-html
