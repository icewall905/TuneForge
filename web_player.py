def run_metadata_update(skip_existing=False):
    """Run metadata update in a background thread"""
    try:
        if not metadata_service:
            logger.error("Cannot update metadata: Metadata service not available")
            return
            
        # Run metadata update
        logger.info(f"Starting metadata update (skip_existing={skip_existing})")
        result = metadata_service.update_all_metadata(status_tracker=METADATA_UPDATE_STATUS, skip_existing=skip_existing)
        
        # Update final status
        METADATA_UPDATE_STATUS.update({
            'running': False,
            'percent_complete': 100,
            'last_updated': datetime.now().isoformat()
        })
        
        # Save database changes if in-memory mode is active
        if DB_IN_MEMORY and main_thread_conn:
            try:
                logger.info("Attempting to save in-memory database after metadata update")
                from db_utils import trigger_db_save
                trigger_db_save(main_thread_conn, DB_PATH)
                logger.info("Successfully saved in-memory database after metadata update")
            except Exception as e:
                logger.error(f"Error saving database after metadata update: {e}")
                # Try direct approach as fallback
                try:
                    logger.info("Trying alternative database save method")
                    main_thread_conn.commit()
                    main_thread_conn.execute("PRAGMA wal_checkpoint")
                    logger.info("Alternative database save successful")
                except Exception as alt_e:
                    logger.error(f"Alternative save also failed: {alt_e}")
        
        logger.info(f"Metadata update completed successfully: {result.get('processed', 0)} processed, {result.get('updated', 0)} updated")
        
    except Exception as e:
        logger.error(f"Error updating metadata: {e}")
        # Update status with error
        METADATA_UPDATE_STATUS.update({
            'running': False,
            'error': str(e),
            'last_updated': datetime.now().isoformat()
        })
