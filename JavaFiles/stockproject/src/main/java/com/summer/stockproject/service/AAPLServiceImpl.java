package com.summer.stockproject.service;

import com.summer.stockproject.dao.AAPLRepository;
import com.summer.stockproject.entity.AAPL;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceContext;
import javax.persistence.Query;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.Date;
import java.util.List;

@Service
public class AAPLServiceImpl implements AAPLService {

    private AAPLRepository aAPLRepository;
    
    @PersistenceContext
    private EntityManager entityManager;

    @Autowired
    public AAPLServiceImpl(AAPLRepository AAPLRepository) {
        this.aAPLRepository = AAPLRepository;
    }

//    @Override
//    public List<AAPL> findBystartDateBetween(Date start, Date end) {
//
//        return  aAPLRepository.findByStartDateBetween(start, end);
//    }

    @Override
    public List<AAPL> findAll() {
        return aAPLRepository.findAll();
    }

    @Override
    public AAPL getByTimePoint(LocalDateTime timepoint) {
        return aAPLRepository.getByTimePoint(timepoint);
    }

    @Override
    public AAPL getById(int theid) {
        return aAPLRepository.getById(theid);
    }

    @Override
    public List<AAPL> findByStartDateBetween(Timestamp start, Timestamp end) {
        return aAPLRepository.findByStartDateBetween(start,end);
    }

    @Override
    public List<AAPL> findBySingleDate(Timestamp date) {
        return aAPLRepository.findBySingleDate(date);
    }

    @Override
    public List<AAPL> universalfind(String tablename, Timestamp start, Timestamp end) {
        // Validate table name contains only letters and numbers to prevent SQL injection
        if (!tablename.matches("^[A-Z0-9]+$")) {
            throw new IllegalArgumentException("Invalid table name: " + tablename);
        }
        
        // Handle META -> FB mapping (Facebook changed ticker from FB to META)
        if (tablename.equals("META")) {
            tablename = "FB";
        }
        
        // Use EntityManager to dynamically build query
        // Use backticks to handle reserved words in MySQL
        String sql = "SELECT * FROM `" + tablename + "` u WHERE u.timePoint >= :start AND u.timePoint <= :end ORDER BY u.timePoint ASC";
        Query query = entityManager.createNativeQuery(sql, AAPL.class);
        query.setParameter("start", start);
        query.setParameter("end", end);
        
        @SuppressWarnings("unchecked")
        List<AAPL> result = query.getResultList();
        return result;
    }


}
