//map centered on gainesville
const map = L.map("map").setView([29.65, -82.33], 12);

//background street map from openstreetmap
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
  maxZoom: 19
}).addTo(map);

//which view the map is showing: gap, need, service or change
let currentView = "gap";

//the drawn tracts, and a lookup from tract id to its shape so the sidebar can find it
let tractLayer = null;
const tractShapes = {};

//tract id of the tract that was clicked, null until one is clicked
let selectedGeoid = null;

//colors for gap, orange = more need than service, blue = more service than need (uf colors)
function gapColor(gap) {
  if (gap > 30) {
    return "#c2360f";
  } else if (gap > 15) {
    return "#fa4616";
  } else if (gap > 0) {
    return "#fdb592";
  } else if (gap > -15) {
    return "#a9b8ee";
  } else if (gap > -30) {
    return "#3a5bd1";
  } else {
    return "#0021a5";
  }
}

//colors for need score, darker orange = more need
function needColor(score) {
  if (score >= 75) {
    return "#c2360f";
  } else if (score >= 60) {
    return "#fa4616";
  } else if (score >= 45) {
    return "#fc8a5e";
  } else if (score >= 30) {
    return "#fdc3a8";
  } else {
    return "#fee6db";
  }
}

//colors for service score, darker blue = more service
function serviceColor(score) {
  if (score >= 75) {
    return "#0021a5";
  } else if (score >= 60) {
    return "#3a5bd1";
  } else if (score >= 45) {
    return "#6f86df";
  } else if (score >= 30) {
    return "#a9b8ee";
  } else {
    return "#dbe2f8";
  }
}

//colors for change in buses nearby, orange = lost service, blue = gained service, gray = no data
function changeColor(change) {
  if (change === null) {
    return "#bbbbbb";
  } else if (change <= -0.4) {
    return "#c2360f";
  } else if (change <= -0.2) {
    return "#fa4616";
  } else if (change < 0) {
    return "#fdb592";
  } else if (change < 0.2) {
    return "#a9b8ee";
  } else {
    return "#3a5bd1";
  }
}

//picks the fill color for a tract based on the current view
function fillColor(tractInfo) {
  if (currentView === "need") {
    return needColor(tractInfo.need_score);
  } else if (currentView === "service") {
    return serviceColor(tractInfo.service_score);
  } else if (currentView === "change") {
    return changeColor(tractInfo["buses_change_%"]);
  } else {
    return gapColor(tractInfo.gap);
  }
}

//how each tract looks, underserved tracts get a thick black outline, clicked tract gets a yellow one
function tractStyle(feature) {
  const tractInfo = feature.properties;

  let outlineColor = "#ffffff";
  let outlineWidth = 1;
  if (tractInfo.category === "underserved") {
    outlineColor = "#000000";
    outlineWidth = 3;
  }
  if (tractInfo.GEOID === selectedGeoid) {
    outlineColor = "#ffd700";
    outlineWidth = 4;
  }

  return {
    fillColor: fillColor(tractInfo),
    fillOpacity: 0.75,
    color: outlineColor,
    weight: outlineWidth
  };
}

//turns a 0-1 share into a percent
function toPercent(share) {
  return Math.round(share * 100) + "%";
}

//turns a change like -0.25 into "-25%", n/a when blank
function toChange(change) {
  if (change === null) {
    return "n/a";
  }
  let changeText = Math.round(change * 100) + "%";
  if (change > 0) {
    changeText = "+" + changeText;
  }
  return changeText;
}

//adds a + in front of positive numbers
function toSigned(number) {
  let numberText = String(Math.round(number));
  if (number > 0) {
    numberText = "+" + numberText;
  }
  return numberText;
}

//details text for the clicked tract
function tractDetails(tractInfo) {
  //"Census Tract 19.02; Alachua County; Florida" -> "Census Tract 19.02"
  const tractName = tractInfo.NAME_y.split(";")[0];

  let details = "<strong>" + tractName + "</strong><br>";
  details = details + tractInfo.category + "<br>";
  details = details + "gap rank: " + tractInfo.gap_rank + " of 51<br><br>";

  //scores
  details = details + "need score: " + Math.round(tractInfo.need_score) + "<br>";
  details = details + "service score: " + Math.round(tractInfo.service_score) + "<br><br>";

  //who lives there
  details = details + "residents: " + tractInfo.B01003_001E.toLocaleString() + "<br>";
  details = details + "households with no car: " + toPercent(tractInfo["no_car_%"]) + "<br>";
  details = details + "below poverty: " + toPercent(tractInfo["poverty_%"]) + "<br>";
  details = details + "age 65+: " + toPercent(tractInfo["senior_citizens_%"]) + "<br>";
  details = details + "college students: " + toPercent(tractInfo["students_%"]) + "<br><br>";

  //bus service now
  details = details + "land within a 5 min walk of a stop: " + toPercent(tractInfo.walking_coverage) + "<br>";
  details = details + "weekday buses within a 5 min walk: " + Math.round(tractInfo.buses_nearby).toLocaleString() + "<br><br>";

  //how service changed since 2023-24
  details = details + "weekday buses nearby in 2023-24: " + Math.round(tractInfo.buses_nearby_2023).toLocaleString() + "<br>";
  details = details + "change since 2023-24: " + toChange(tractInfo["buses_change_%"]);

  return details;
}

//shows a tract's details in the sidebar and highlights it on the map
function showDetails(tractInfo) {
  document.getElementById("details").innerHTML = tractDetails(tractInfo);
  selectedGeoid = tractInfo.GEOID;
  tractLayer.setStyle(tractStyle);
}

//legend title and color labels for each view
const legendItems = {
  gap: {
    title: "need minus service",
    items: [["#c2360f", "+30 or more"], ["#fa4616", "+15 to +30"], ["#fdb592", "0 to +15"],
            ["#a9b8ee", "0 to -15"], ["#3a5bd1", "-15 to -30"], ["#0021a5", "-30 or less"]]
  },
  need: {
    title: "need score",
    items: [["#c2360f", "75+"], ["#fa4616", "60 to 75"], ["#fc8a5e", "45 to 60"],
            ["#fdc3a8", "30 to 45"], ["#fee6db", "under 30"]]
  },
  service: {
    title: "service score",
    items: [["#0021a5", "75+"], ["#3a5bd1", "60 to 75"], ["#6f86df", "45 to 60"],
            ["#a9b8ee", "30 to 45"], ["#dbe2f8", "under 30"]]
  },
  change: {
    title: "weekday buses nearby, 2023-24 to fall 2026",
    items: [["#c2360f", "lost 40% or more"], ["#fa4616", "lost 20 to 40%"], ["#fdb592", "lost 0 to 20%"],
            ["#a9b8ee", "gained 0 to 20%"], ["#3a5bd1", "gained 20% or more"], ["#bbbbbb", "no buses in 2023-24"]]
  }
};

//legend in the bottom right corner
let legendBox = null;

//rebuilds the legend for the current view
function updateLegend() {
  const view = legendItems[currentView];
  let legendText = "<strong>" + view.title + "</strong><br>";
  for (let i = 0; i < view.items.length; i = i + 1) {
    const color = view.items[i][0];
    const label = view.items[i][1];
    legendText = legendText + '<span style="background:' + color + '"></span>' + label + "<br>";
  }
  legendText = legendText + '<span style="background:white; border:3px solid black; width:10px; height:10px"></span>underserved';
  legendBox.innerHTML = legendText;
}

const legend = L.control({ position: "bottomright" });
legend.onAdd = function () {
  legendBox = L.DomUtil.create("div", "legend");
  updateLegend();
  return legendBox;
};
legend.addTo(map);

//switches the map view, recolors the tracts, updates the legend and buttons
function showView(viewName) {
  currentView = viewName;
  if (tractLayer !== null) {
    tractLayer.setStyle(tractStyle);
  }
  updateLegend();

  //highlights the button that was clicked
  const viewNames = ["gap", "need", "service", "change"];
  for (let i = 0; i < viewNames.length; i = i + 1) {
    const button = document.getElementById("view-" + viewNames[i]);
    if (viewNames[i] === viewName) {
      button.classList.add("active");
    } else {
      button.classList.remove("active");
    }
  }
}

//view buttons
document.getElementById("view-gap").addEventListener("click", function () {
  showView("gap");
});
document.getElementById("view-need").addEventListener("click", function () {
  showView("need");
});
document.getElementById("view-service").addEventListener("click", function () {
  showView("service");
});
document.getElementById("view-change").addEventListener("click", function () {
  showView("change");
});

//zooms to a tract and shows its details
function zoomToTract(geoid) {
  const shape = tractShapes[geoid];
  map.fitBounds(shape.getBounds(), { maxZoom: 14 });
  showDetails(shape.feature.properties);
}

//sidebar list of the 10 biggest gaps, click one to zoom to it
function buildGapList(features) {
  //sort tracts by gap rank, 1 first
  const sortedFeatures = features.slice();
  sortedFeatures.sort(function (a, b) {
    return a.properties.gap_rank - b.properties.gap_rank;
  });

  const gapList = document.getElementById("gap-list");
  for (let i = 0; i < 10; i = i + 1) {
    const tractInfo = sortedFeatures[i].properties;
    const tractName = tractInfo.NAME_y.split(";")[0];

    const listItem = document.createElement("li");
    listItem.textContent = tractName + " (gap " + toSigned(tractInfo.gap) + ")";
    listItem.addEventListener("click", function () {
      zoomToTract(tractInfo.GEOID);
    });
    gapList.appendChild(listItem);
  }
}

//fills the key findings box from summary.json made by location.py
function showSummary(summary) {
  let summaryText = "";
  summaryText = summaryText + '<div class="stat"><strong>' + summary.underserved_tracts + " of " + summary.scored_tracts + "</strong>neighborhoods underserved</div>";
  summaryText = summaryText + '<div class="stat"><strong>' + summary.underserved_residents.toLocaleString() + "</strong>residents in underserved neighborhoods</div>";
  summaryText = summaryText + '<div class="stat"><strong>' + toPercent(summary.car_free_beyond_walk) + "</strong>of car-free households live beyond a 5 min walk of a stop</div>";
  summaryText = summaryText + '<div class="stat"><strong>' + toChange(summary.departures_2026 / summary.departures_2023 - 1) + "</strong>weekday bus departures, 2023-24 to fall 2026</div>";
  summaryText = summaryText + '<div class="stat"><strong>' + toChange(summary.high_need_change) + " vs " + toChange(summary.low_need_change) + "</strong>change in nearby buses, high need vs low need neighborhoods</div>";
  document.getElementById("summary").innerHTML = summaryText;
}

//loads the data made by location.py and builds the dashboard
async function loadDashboard() {
  //headline numbers for the findings box
  const summaryResponse = await fetch("../data/summary.json");
  const summary = await summaryResponse.json();
  showSummary(summary);

  //scored tracts for the map
  const tractResponse = await fetch("../data/scored_tracts.geojson");
  const scoredTracts = await tractResponse.json();

  tractLayer = L.geoJSON(scoredTracts, {
    style: tractStyle,
    onEachFeature: function (feature, layer) {
      //clicking a tract shows its details in the sidebar
      layer.on("click", function () {
        showDetails(feature.properties);
      });
      //save each shape by tract id so the sidebar can find it
      tractShapes[feature.properties.GEOID] = layer;
    }
  });
  tractLayer.addTo(map);

  //zoom so every scored tract fits on screen
  map.fitBounds(tractLayer.getBounds());

  buildGapList(scoredTracts.features);
}

loadDashboard();