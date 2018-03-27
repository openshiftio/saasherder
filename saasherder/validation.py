class ValidationRule(object):
    def __init__(self, template):
        self.template = template

        self.objects = {}
        for obj in template['objects']:
            kind = obj['kind']
            self.objects.setdefault(kind, []).append(obj)

    def error(self, msg):
        return "{}: {}".format(self.__class__.__name__, msg)

class ContainerRequestsLimitsRule(ValidationRule):
    def error_msg(self, dc_name, container_name, msg):
        error_msg = "dc {}, container {}: {}".format(dc_name, container_name, msg)
        return self.error(error_msg)

    def validate(self):
        errors = []
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

                    if not memory_limit:
                        errors.append(self.error_msg(dc_name, container_name, 'Undefined memory limit'))

                    if not cpu_limit:
                        errors.append(self.error_msg(dc_name, container_name, 'Undefined cpu limit'))

                    if not memory_request:
                        errors.append(self.error_msg(dc_name, container_name, 'Undefined memory request'))

                    if not cpu_request:
                        errors.append(self.error_msg(dc_name, container_name, 'Undefined cpu request'))

        return errors

VALIDATION_RULES = [ContainerRequestsLimitsRule]
