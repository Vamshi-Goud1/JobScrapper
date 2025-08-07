from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import pandas as pd
import logging
from datetime import datetime
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="JobSpy API",
    description="API wrapper for JobSpy job scraping library",
    version="1.0.0",
    docs_url="/",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class JobSearchRequest(BaseModel):
    search_term: str = Field(..., description="Job title or keywords")
    location: str = Field(default="", description="Job location")
    site_name: List[str] = Field(default=["indeed"], description="Job sites to search")
    results_wanted: Optional[int] = Field(default=10, ge=1, le=50)
    is_remote: Optional[bool] = Field(default=False)

class JobSearchResponse(BaseModel):
    success: bool
    message: str
    total_jobs: int
    jobs: List[dict]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": sys.version.split()[0],
        "working_directory": os.getcwd()
    }

@app.get("/test")
async def test_jobspy():
    """Test if JobSpy can be imported and works"""
    try:
        # Test JobSpy import
        from jobspy import scrape_jobs
        logger.info("JobSpy imported successfully")
        
        return {
            "status": "success",
            "message": "JobSpy is working correctly",
            "jobspy_imported": True
        }
    except Exception as e:
        logger.error(f"JobSpy test failed: {e}")
        return {
            "status": "error", 
            "message": f"JobSpy test failed: {str(e)}",
            "jobspy_imported": False
        }

@app.get("/search-jobs-simple")
async def search_jobs_simple(
    search_term: str = Query(..., description="Job title to search for"),
    location: str = Query("", description="Location (optional)"),
    results_wanted: int = Query(5, ge=1, le=20, description="Number of results (1-20)")
):
    """Simple job search endpoint"""
    try:
        logger.info(f"Searching for: {search_term} in {location}")
        
        # Import JobSpy
        from jobspy import scrape_jobs
        
        # Perform search
        jobs_df = scrape_jobs(
            search_term=search_term,
            location=location,
            site_name=["indeed"],
            results_wanted=results_wanted
        )
        
        if jobs_df is None or jobs_df.empty:
            return {
                "success": True,
                "message": "No jobs found for the search criteria",
                "total_jobs": 0,
                "jobs": []
            }
        
        # Convert to list and clean NaN values
        jobs_list = jobs_df.to_dict('records')
        for job in jobs_list:
            for key, value in job.items():
                if pd.isna(value):
                    job[key] = None
        
        logger.info(f"Found {len(jobs_list)} jobs")
        
        return {
            "success": True,
            "message": f"Found {len(jobs_list)} jobs",
            "total_jobs": len(jobs_list),
            "jobs": jobs_list
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/search-jobs", response_model=JobSearchResponse)
async def search_jobs_post(request: JobSearchRequest):
    """Advanced job search endpoint"""
    try:
        logger.info(f"POST search: {request.search_term} in {request.location}")
        
        from jobspy import scrape_jobs
        
        # Prepare search parameters
        search_params = {
            "search_term": request.search_term,
            "location": request.location,
            "site_name": request.site_name,
            "results_wanted": request.results_wanted,
            "is_remote": request.is_remote
        }
        
        # Remove empty values
        search_params = {k: v for k, v in search_params.items() if v}
        
        jobs_df = scrape_jobs(**search_params)
        
        if jobs_df is None or jobs_df.empty:
            return JobSearchResponse(
                success=True,
                message="No jobs found",
                total_jobs=0,
                jobs=[]
            )
        
        jobs_list = jobs_df.to_dict('records')
        
        # Clean NaN values
        for job in jobs_list:
            for key, value in job.items():
                if pd.isna(value):
                    job[key] = None
        
        return JobSearchResponse(
            success=True,
            message=f"Found {len(jobs_list)} jobs",
            total_jobs=len(jobs_list),
            jobs=jobs_list
        )
        
    except Exception as e:
        logger.error(f"POST search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/supported-sites")
async def get_supported_sites():
    """Get supported job sites"""
    return {
        "supported_sites": ["indeed", "linkedin", "glassdoor", "google", "ziprecruiter"],
        "note": "Indeed is most reliable for testing"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting JobSpy API on port {port}")
    print(f"📍 API docs will be available at: http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)