import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const city = request.nextUrl.searchParams.get("city")?.trim();

  if (!city) {
    return NextResponse.json({ error: "city is required" }, { status: 400 });
  }

  try {
    const geocodingUrl = new URL(
      "https://geocoding-api.open-meteo.com/v1/search"
    );
    geocodingUrl.searchParams.set("name", city);
    geocodingUrl.searchParams.set("count", "1");
    geocodingUrl.searchParams.set("language", "en");
    geocodingUrl.searchParams.set("format", "json");

    const geocodingResponse = await fetch(geocodingUrl, { cache: "no-store" });

    if (!geocodingResponse.ok) {
      return NextResponse.json(
        { error: "weather location lookup failed" },
        { status: 502 }
      );
    }

    const geocodingData = await geocodingResponse.json();
    const place = geocodingData?.results?.[0];

    if (
      typeof place?.latitude !== "number" ||
      typeof place?.longitude !== "number"
    ) {
      return NextResponse.json(
        { error: "location could not be resolved" },
        { status: 404 }
      );
    }

    const weatherUrl = new URL("https://api.open-meteo.com/v1/forecast");
    weatherUrl.searchParams.set("latitude", String(place.latitude));
    weatherUrl.searchParams.set("longitude", String(place.longitude));
    weatherUrl.searchParams.set("current", "temperature_2m");
    weatherUrl.searchParams.set("timezone", "UTC");

    const weatherResponse = await fetch(weatherUrl, { cache: "no-store" });

    if (!weatherResponse.ok) {
      return NextResponse.json(
        { error: "weather provider request failed" },
        { status: 502 }
      );
    }

    const weatherData = await weatherResponse.json();
    const temperature = weatherData?.current?.temperature_2m;
    const observedAt = weatherData?.current?.time;

    if (
      typeof temperature !== "number" ||
      typeof observedAt !== "string"
    ) {
      return NextResponse.json(
        { error: "weather provider returned incomplete data" },
        { status: 502 }
      );
    }

    return NextResponse.json({
      location: city,
      temperature_c: temperature,
      observed_at: observedAt,
    });
  } catch {
    return NextResponse.json(
      { error: "unable to retrieve weather data" },
      { status: 500 }
    );
  }
}
