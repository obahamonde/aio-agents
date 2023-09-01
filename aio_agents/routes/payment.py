from aiofauna import *

from ..data import *
from ..schemas import *
from ..services import *

logger = setup_logging(__name__)


class PaymentsRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(prefix="/api", tags=["Load"], *args, **kwargs)
        self.llm = LLMStack()

        @self.post("/payments/callback")
        async def payments_webhook_endpoint(request: Request):
            data = await request.json()
            logger.info("Received webhook: %s", data)
            parsed = to_json(data)
            ses = Session().client("ses")
            ses.send_email(
                Source="oscar.bahamonde@aiofauna.com",
                Destination={"ToAddresses": ["oscar.bahamonde@aiofauna.com"]},
                Message={
                    "Subject": {"Data": "Payment received"},
                    "Body": {"Text": {"Data": f"Payment received:\n{parsed}"}},
                },
            )
            return {"message": "Success"}

        @self.get("/payments")
        async def get_paypal_buttons(request: Request):
            html = """
<html lang="en">
<title>AioFauna Sponsorship</title>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PayPal JS SDK Standard Integration</title>
    <link rel="icon" href="/logo.png" type="image/png">
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.15/dist/tailwind.min.css" rel="stylesheet">
</head>

<body class="bg-gray-100 h-screen font-sans">
    <div class="container mx-auto h-full flex justify-center items-center">
        <div class="w-1/3 bg-white rounded shadow-lg p-8 m-4">
            <img src="/logo.png" alt="AioFauna logo" class="mx-auto w-24 mb-6">
            <h1 class="block w-full text-center text-gray-800 text-2xl mb-6">
                Thanks for supporting AioFauna!
            </h1>
            <p class="text-center text-gray-600 mb-6">Choose your preferred payment method below.</p>
<div id="paypal-button-container-P-8UD08478HH089752XMTXG5OQ" class="mb-4"></div>
                    </div>
    </div>

<script src="https://www.paypal.com/sdk/js?client-id=AXyvh4Qwvj6M8YtSvSAHjWwq2h2O-5j5z0h71rU-tAbXGAz-lYGSaBFtIh7D83sIt5GcckunfD78B1ea&vault=true&intent=subscription" data-sdk-integration-source="button-factory"></script>
<script>
  paypal.Buttons({
      style: {
          shape: 'pill',
          color: 'black',
          layout: 'vertical',
          label: 'subscribe'
      },
      createSubscription: function(data, actions) {
        return actions.subscription.create({
          /* Creates the subscription */
          plan_id: 'P-8UD08478HH089752XMTXG5OQ'
        });
      },
      onApprove: function(data, actions) {
        alert(data.subscriptionID); // You can add optional success message for the subscriber here
      }
  }).render('#paypal-button-container-P-8UD08478HH089752XMTXG5OQ'); // Renders the PayPal button
</script>
</body>
</html>

"""
            return Response(text=html, content_type="text/html")
