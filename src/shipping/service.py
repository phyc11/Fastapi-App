from datetime import datetime, timezone
from uuid import uuid4

VALID_TRACKING_STATUSES = {"preparing", "picked_up", "in_transit", "delivered"}


class ShippingAddress:
    def __init__(
        self,
        user_id: str,
        full_name: str,
        phone: str,
        street_address: str,
        city: str,
        is_default: bool = False,
    ) -> None:
        normalized_name = full_name.strip()
        normalized_phone = phone.strip()
        normalized_street = street_address.strip()
        normalized_city = city.strip()

        if not normalized_name:
            raise ValueError("full_name must not be empty")
        if not normalized_phone:
            raise ValueError("phone must not be empty")
        if not normalized_street:
            raise ValueError("street_address must not be empty")
        if not normalized_city:
            raise ValueError("city must not be empty")

        self.address_id = uuid4().hex
        self.user_id = user_id
        self.full_name = normalized_name
        self.phone = normalized_phone
        self.street_address = normalized_street
        self.city = normalized_city
        self.is_default = is_default
        self.created_at = datetime.now(timezone.utc)


class TrackingEvent:
    def __init__(
        self,
        status: str,
        location: str,
        description: str,
        timestamp: datetime | None = None,
    ) -> None:
        status_key = status.strip().lower()
        if status_key not in VALID_TRACKING_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(VALID_TRACKING_STATUSES)}"
            )

        self.event_id = uuid4().hex
        self.status = status_key
        self.location = location.strip()
        self.description = description.strip()
        self.timestamp = timestamp or datetime.now(timezone.utc)


class ShipmentTracking:
    def __init__(
        self,
        tracking_number: str,
        order_id: str,
        carrier: str = "StandardExpress",
    ) -> None:
        self.tracking_number = tracking_number.strip()
        self.order_id = order_id.strip()
        self.carrier = carrier.strip()
        self.current_status = "preparing"
        self.history: list[TrackingEvent] = []
        self.add_event(
            status="preparing",
            location="Warehouse",
            description="Shipment information received",
        )

    def add_event(
        self,
        status: str,
        location: str,
        description: str,
        timestamp: datetime | None = None,
    ) -> TrackingEvent:
        event = TrackingEvent(status, location, description, timestamp)
        self.history.append(event)
        self.current_status = event.status
        return event


class ShippingService:
    def __init__(self) -> None:
        self.user_addresses: dict[str, list[ShippingAddress]] = {}
        self.shipments: dict[str, ShipmentTracking] = {}

    def add_address(
        self,
        user_id: str,
        full_name: str,
        phone: str,
        street_address: str,
        city: str,
        is_default: bool = False,
    ) -> ShippingAddress:
        addresses = self.user_addresses.setdefault(user_id, [])

        # If this is user's first address, force it to be default
        if not addresses or is_default:
            is_default = True
            for addr in addresses:
                addr.is_default = False

        address = ShippingAddress(
            user_id=user_id,
            full_name=full_name,
            phone=phone,
            street_address=street_address,
            city=city,
            is_default=is_default,
        )
        addresses.append(address)
        return address

    def get_user_addresses(self, user_id: str) -> list[ShippingAddress]:
        return self.user_addresses.get(user_id, [])

    def set_default_address(
        self, user_id: str, address_id: str
    ) -> ShippingAddress:
        addresses = self.get_user_addresses(user_id)
        target = None
        for addr in addresses:
            if addr.address_id == address_id:
                target = addr
                break

        if target is None:
            raise KeyError("address not found")

        for addr in addresses:
            addr.is_default = (addr.address_id == address_id)

        return target

    def calculate_fee(
        self, city: str, weight_kg: float, order_amount: float = 0.0
    ) -> dict:
        if weight_kg <= 0:
            raise ValueError("weight_kg must be positive")
        if order_amount < 0:
            raise ValueError("order_amount must be non-negative")

        # Free shipping for order_amount >= 500.0
        if order_amount >= 500.0:
            return {
                "city": city.strip(),
                "weight_kg": float(weight_kg),
                "base_fee": 0.0,
                "weight_fee": 0.0,
                "total_fee": 0.0,
                "free_shipping": True,
            }

        base_fee = 30.0
        # Extra 5.0 per kg over 1kg
        weight_fee = max(0.0, (weight_kg - 1.0) * 5.0)
        total_fee = round(base_fee + weight_fee, 2)

        return {
            "city": city.strip(),
            "weight_kg": float(weight_kg),
            "base_fee": round(base_fee, 2),
            "weight_fee": round(weight_fee, 2),
            "total_fee": total_fee,
            "free_shipping": False,
        }

    def register_shipment(
        self,
        tracking_number: str,
        order_id: str,
        carrier: str = "StandardExpress",
    ) -> ShipmentTracking:
        shipment = ShipmentTracking(tracking_number, order_id, carrier)
        self.shipments[shipment.tracking_number] = shipment
        return shipment

    def update_shipment_status(
        self,
        tracking_number: str,
        status: str,
        location: str,
        description: str,
    ) -> ShipmentTracking:
        shipment = self.shipments.get(tracking_number)
        if shipment is None:
            raise KeyError("tracking number not found")
        shipment.add_event(status, location, description)
        return shipment

    def track_shipment(self, tracking_number: str) -> ShipmentTracking:
        shipment = self.shipments.get(tracking_number)
        if shipment is None:
            raise KeyError("tracking number not found")
        return shipment
