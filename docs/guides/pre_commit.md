# Pre commit

## Maintenance of the file

### Manually check the latest release versions

1. open the repo link
2. go to releases
3. get the latest stable version

For
* pre-commit hooks versions
* yelp detect-secrets

### Match the uv versions of the tools

1. update the tool with [uv](./uv.md)
2. run the command to get the version
3. update the rev in this file (note that some revs have a "v" prefix)

For
* uv itself
* ruff
* pyright
* nbstripout
