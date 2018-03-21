class ValidationRuleError(Exception):
    pass

class ValidationRule(object):
    def __init__(self, template):
        self.template = template

        self.objects = {}
        for obj in template['objects']:
            kind = obj['kind']
            self.objects.setdefault(kind, []).append(obj)

    def error(self, msg):
        name = self.__class__.__name__
        raise ValidationRuleError("{}: {}".format(name, msg))

class ContainerRequestsLimitsRule(ValidationRule):
    def validate(self):
        for dc in self.objects['DeploymentConfig']:
            for container in dc['spec']['template']['spec']['containers']:
                resources = container.get('resources', {})

                limits = resources.get('limits', {})
                memory_limit = limits.get('memory')
                cpu_limit = limits.get('cpu')

                requests = resources.get('requests', {})
                memory_request = requests.get('memory')
                cpu_request = requests.get('cpu')

                if None in [memory_limit, cpu_limit, memory_request, cpu_request]:
                    dc_name = dc.get('metadata', {}).get('name', 'unnamed_dc')
                    container_name = container.get('name', 'unnamed_container')

                    error_msg = "dc: {}, container: {}.".format(dc_name, container_name)

                    if not memory_limit:
                        error_msg += ' Undefined memory limit.'

                    if not cpu_limit:
                        error_msg += ' Undefined cpu limit.'

                    if not memory_request:
                        error_msg += ' Undefined memory request.'

                    if not cpu_request:
                        error_msg += ' Undefined cpu request.'

                    self.error(error_msg)

VALIDATION_RULES = [ContainerRequestsLimitsRule]
