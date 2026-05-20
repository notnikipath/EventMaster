from locust import HttpUser, between, task


class GatewayUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def dashboard(self):
        self.client.get("/dashboard/EV-CONCERT-001")

    @task(1)
    def services_health(self):
        self.client.get("/services/health")
