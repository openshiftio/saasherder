# SaaS

There are many services in OpenShift.io SaaS. To track what is deployed in production and to be able redeploy the very same versions of all components quickly, we created this SaaS Herder tool. It helps helps to track all the OpenShift templates in various repositories and to process them for deployment.

Services and their deployment templates are tracked in other repositories. OpenShift.io and associated services are currently tracked in these repositories:

* https://github.com/openshiftio/saas-openshiftio
* https://github.com/openshiftio/saas-analytics
* https://github.com/openshiftio/saas-launchpad

# The Process

Repositories above not only contain references to all OpenShift templates for OpenShift.io, but also serve to enforce promote-to-prod process for our services. Whole process is as follows:

1. Code is checked in project git repository (e.g. new commit `abcd1234`)
2. CI build is kicked off (e.g. for the commit `abcd1234`)
3. If the build is successful, image tagged with commit hash is pushed to repository (e.g. `core:abcd12`)
4. New image is deployed to staging cluster (e.g. `oc process -f openshift/template.yaml IMAGE_TAG=abcd12 | oc apply -f -`)
5. A developer verifies new dpeloyment in stage and creates a PR, which changes commit hash for the given service, for a tracking repository (e.g. `hash:` is updated in https://github.com/openshiftio/saas-openshiftio/blob/master/dsaas-services/core.yaml)
6. PR is merged (i.e. this is the **promote-to-prod** manual step)
7. Once merged, CI job is kicked off, which deploys new version to production (e.g. checkouts a template from git repo for a given commit hash, processes it with `$IMAGE_TAG` and performs `oc apply`)

# Tracking repositories
## Service YAML

```
services:
- hash: aab9fc5fa5c24360079998f2209b2b55c3af29ae
  hash_length: 6
  name: some-name
  path: /openshift/template.yaml
  url: https://github.com/org/repo/
  skip: True
  parameters:
    SOME_PARAM: some_value
  environments:
  - name: production
    parameters:
      SOME_PARAM: prod_value
    skip: True
```

* *hash*: Commit hash or branch which is used a) for downloading OpenShift template and b) to generate image tag for template processing (`master` is translated to `latest`)
* *hash_length*: Number of characters to be used from *hash* as an image tag
* *name*: Name of the service
* *path*: Path to the template in the repo
* *url*: URL of the repository which contains the template
* *skip*: False by default, if True, the service will be skipped from processing (i.e. template will not be processed and output file for service will not be produced)
* *parameters*: An object where key is the parameter name and value is the parameter value. These parameters will be added to `oc process` when processing the template
* *environments*: A list where you can specify multiple environments which can be selected by passing an argument `--environment`. Values in a given environment will override
  values in the top level section. Anything can be overridden but `name`, `url` and `hash`.

## Config YAML

Config file should be located in the root of the repository (to be automatically picked up by the tool). It helps SaaS Herder to find tracked services and provides default locations for download and processing of the files.

It can contain multiple contexts, which can point to multiple service folders. We use this to map service yaml files to projects in OpenShift - i.e. context `dsaas` will map to project `dsaas-production`. 

```
current: dsaas
contexts:
- name: dsaas
  data:
    output_dir: dsaas-processed
    services_dir: dsaas-services
    templates_dir: dsaas-templates 
```

# Basic Usage

## Install

```
python setup.py install
```

## Run

All of the following command assume being run in the tracking repository clone (e.g. https://github.com/openshiftio/saas-openshiftio)

```
saasherder -h
```

You can pull all the templates by running the following

```
saasherder --context dsaas pull
```

You'll find the downloaded templates in `dsaas-templates/` dir (as defined in `config.yaml` in the tracking repository - https://github.com/openshiftio/saas-openshiftio/blob/master/config.yaml).

You can update commit hash in the `$service.yaml` file by running

```
saasherder --context dsaas update -o foo.yaml hash core b52c33c8f6c40a5dca70c8b3c25387b01881bf2d
```

This will create file `foo.yaml` which will be a copy of file `dsaas-services/core.yaml` with updated commit hash for `core` service.

You can also process downloaded templates to use commit hash as an image tag.

```
saasherder  --context dsaas template --output-dir test tag
```

This will take templates in `dsaas-templates/` and commit hashes in `dsaas-services/*.yaml` and produce processed template to `test/` directory.
It requires `oc` binary to be present on path and logged into some OpenShift instance (it actually calls `oc process` to leverage existing tooling). If you don't want to, or cannot login to OpenShift instance for processing, you can use `--local` option

```
saasherder  --context dsaas template --output-dir test --local tag 
```


### Environments

If you deploy to multiple environments (like we do, e.g. `production`, `staging`, etc.) you might need to slightly adjust how your service is deployed. There is a structure `environments` for it (see above for explanation). Let's assume you are now deploying to `production`. As you can change `path` in service yaml file for environments (to ensure upgrade path without breaking other environments), first pull templates with environment specified

```
saasherder --context dsaas --environment production pull
```

Next step is to process templates - and again, we need to specify the environment to make sure right values (e.g. parameters) are used

```
saasherder --context dsaas --environment production template tag
```

To give you real world example - we have services which set `replicas` through parameters to make it easy to scale in a predictable way. In production environment, we'll want to scale to 100 pods. But in staging environment we will be fine with 10. To do this is as simple as adding

```
environments:
- name: production
  parameters:
    REPLICAS: 100
- name: staging
  parameters:
    REPLICAS: 10
```

Assuming you have parameter `REPLICAS` in your OpenShift template.

Another example might be when adding new service. You want to deploy to staging, catch all bugs and then deploy to production. You can do it simply by adding

```
environments:
- name: production
  skip: True
```

This snippet will ensure your new service will skip deployment to production, but will still deploy for other environments and also if there is no environment given to CLI.

## Test

There are couple tests for SaaS Herder. To run them, you can use included `tests/Dockerfile.test`

```
docker build -t saasherder-test -f tests/Dockerfile.test .
```

To run tests, simply run container

```
docker run -it --rm saasherder-test
```

If you make changes to code or tests, you can check them in the container without rebuild

```
docker run -it --rm -v $PWD/tests:/opt/saasherder/tests -v $PWD/saasherder:/opt/saasherder/saasherder saasherder-test
```

## dsaas-tracking-services
these are tracking services that we are not deploying via saas, but come via another pipeline
we still need to track where to get the content, and the ver deployed 

